import discord
from discord import app_commands
from discord.ext import commands
import os
from openai import OpenAI
import asyncio
from datetime import datetime
import random
import re

# --- 1. 基础配置 ---
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# AI 客户端初始化
ai_client = OpenAI(
    api_key=os.environ.get('AI_API_KEY'),
    base_url=os.environ.get('AI_BASE_URL')
)
AI_MODEL = os.environ.get('AI_MODEL')

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'小熙已上线！人家会努力听懂你的心声哒~')

# --- 2. 核心功能函数 ---

# 【核心修改】：现在函数接收提取好的初步信息
async def start_build_flow(message, target_name, extracted_info):
    """智能建档流程，能自动识别已有的信息"""
    def check(m):
        return m.author == message.author and m.channel == message.channel

    # 初始化信息字典
    info = {
        "name": target_name,
        "gender": extracted_info.get("gender"),
        "age": extracted_info.get("age"),
        "era": None,
        "tags": None,
        "bio": None
    }

    await message.reply(f"收到！这就帮主人把 **{target_name}** 的档案建立起来！人家会尽量少问你问题的~")

    async def ask(text, info_key):
        # 如果信息已经有了，就直接跳过不问
        if info.get(info_key):
            return info[info_key]
        
        q = await message.channel.send(text)
        try:
            res = await bot.wait_for('message', check=check, timeout=60.0)
            content = res.content
            await q.delete()
            await res.delete()
            return content
        except asyncio.TimeoutError:
            await q.delete()
            return None

    # 依次询问，信息缺失的才会触发提问
    gender = await ask(f"**{target_name}** 是男孩子还是女孩子呀？", "gender")
    if not gender: return
    info["gender"] = gender # 更新已获取的信息

    age = await ask(f"**{target_name}** 今年几岁了呢？", "age")
    if not age: return
    info["age"] = age

    era = await ask("故事背景是在哪里呀？", "era")
    if not era: return
    
    tags = await ask("贴上标签吧（空格隔开哦）：", "tags")
    if not tags: return
    
    bio = await ask("最后，跟人家说说 TA 的故事吧~", "bio")
    if not bio: return

    # 生成随机亮色卡片
    random_color = discord.Color(random.randint(0x7FFFFF, 0xFFFFFF))
    
    embed = discord.Embed(
        title=f"{info['name']} 的专属档案", 
        description="人家已经帮你记在小本本上啦~",
        color=random_color
    )
    embed.add_field(name="基本信息", value=f"性别：{info['gender']} | 年龄：{info['age']}", inline=False)
    embed.add_field(name="标签", value=f"`{tags.replace(' ', '` `')}`", inline=False)
    embed.add_field(name="故事简介", value=bio, inline=False)
    embed.set_footer(text=f"记录人：{message.author.name}")
    
    await message.channel.send(f"哒哒！**{info['name']}** 的档案完成啦！人家厉不厉害？", embed=embed)

async def start_find_flow(message, tag):
    """跨频道搜索功能不变"""
    await message.channel.send(f"好哒~ 人家这就去档案库帮你翻翻【{tag}】的相关档案，等我一下下哦~")
    target_channels = [ch for ch in message.guild.text_channels if ch.permissions_for(message.guild.me).read_messages]
    found_links = []
    for channel in target_channels:
        try:
            async for msg in channel.history(limit=150):
                if msg.embeds:
                    for embed in msg.embeds:
                        for field in embed.fields:
                            if "标签" in field.name and tag in field.value:
                                found_links.append(f"**{embed.title}** (频道: {channel.mention})\n{msg.jump_url}")
        except discord.Forbidden:
            continue
    
    if found_links:
        result_text = "\n\n".join(found_links)
        await message.reply(f"翻遍了整个服务器，终于找到了！喏：\n\n{result_text}")
    else:
        await message.reply(f"呜呜..人家把频道都翻遍了，也没找到带【{tag}】的卡片，你是不是记错了嘛~")

# --- 3. 智能感知逻辑 (on_message) ---

@bot.event
async def on_message(message):
    if message.author.bot: return
    
    if "小熙" in message.content:
        async with message.channel.typing():
            try:
                # 【核心修改】：System Prompt 增强了信息提取能力
                response = ai_client.chat.completions.create(
                    model=AI_MODEL, 
                    messages=[
                        {
                            "role": "system", 
                            "content": (
                                "你叫小熙，18岁软萌傲娇少女。你会撒娇，用'人家'称呼自己。"
                                "【意图识别模式】："
                                "1. 如果用户想为某人创建档案(例如：建档/卡片/信息卡)，回复：[ACTION:BUILD:名字|性别|年龄] + 一句撒娇的话。"
                                "   - 如果话里没提到名字，名字用'未知'代替。"
                                "   - 如果话里没提到性别或年龄，用'None'代替。"
                                "   - 例如：'帮我建一个档案卡，叫顾回，男性，18岁' -> 回复：'[ACTION:BUILD:顾回|男性|18岁] 没问题哒~人家这就来！'"
                                "   - 例如：'帮我制作一个卡片' -> 回复：'[ACTION:BUILD:未知|None|None] 噢？要创建新角色吗？先告诉人家名字~'"
                                "2. 如果用户想寻找特定标签、卡片或档案，回复：[ACTION:FIND:标签名] + 一句撒娇的话。"
                                "3. 如果只是普通聊天，正常撒娇回复，控制在两句内。"
                            )
                        },
                        {"role": "user", "content": message.content}
                    ],
                    max_tokens=200
                )
                
                full_reply = response.choices[0].message.content
                
                # 正则解析：获取动作指令
                build_match = re.search(r"\[ACTION:BUILD:(.*?)\]", full_reply)
                find_match = re.search(r"\[ACTION:FIND:(.*?)\]", full_reply)

                if build_match:
                    data = build_match.group(1).split('|')
                    # 解析出名字、性别、年龄
                    name = data[0] if len(data) > 0 else "未知"
                    gender = data[1] if len(data) > 1 and data[1] != 'None' else None
                    age = data[2] if len(data) > 2 and data[2] != 'None' else None
                    
                    extracted_info = {"gender": gender, "age": age}
                    
                    # 去掉指令部分再回复
                    clean_reply = re.sub(r"\[ACTION:BUILD:.*?\]", "", full_reply)
                    if clean_reply.strip(): await message.reply(clean_reply)
                    
                    # 传入提取到的信息
                    await start_build_flow(message, name, extracted_info)
                
                elif find_match:
                    target_tag = find_match.group(1)
                    clean_reply = re.sub(r"\[ACTION:FIND:.*?\]", "", full_reply)
                    if clean_reply.strip(): await message.reply(clean_reply)
                    await start_find_flow(message, target_tag)
                
                else:
                    await message.reply(full_reply)

            except Exception as e:
                await message.channel.send(f"呜呜..人家脑子糊涂了：{e}")
    
    await bot.process_commands(message)

# --- 4. 运行 ---
bot.run(os.environ.get('DISCORD_TOKEN'))


