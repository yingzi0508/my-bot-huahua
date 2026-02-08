import discord
from discord import app_commands
from discord.ext import commands
import os
from openai import OpenAI
import asyncio
from datetime import datetime
import random
import re # 用于正则表达式解析

# --- 1. 基础配置 ---
# Intents 是机器人的感知权限，必须开启 message_content 才能听到“小熙”
intents = discord.Intents.default()
intents.message_content = True 
intents.members = True # 开启成员权限，获取服务器信息
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 2. AI 客户端初始化 ---
# 确保在 Zeabur 变量里配置了这些，且 AI_BASE_URL 结尾加上 /v1
ai_client = OpenAI(
    api_key=os.environ.get('AI_API_KEY'),
    base_url=os.environ.get('AI_BASE_URL')
)
AI_MODEL = os.environ.get('AI_MODEL')

@bot.event
async def on_ready():
    # 同步斜杠指令到 Discord 服务器
    await bot.tree.sync()
    print(f'小熙已上线！人家会努力听懂你的心声哒~')

# --- 3. 核心功能函数 ---

async def start_build_flow(message, target_name):
    """自动触发的建档流程"""
    def check(m):
        return m.author == message.author and m.channel == message.channel

    await message.reply(f"你要给 **{target_name}** 建档吗？既然你都这么说了，人家肯定会帮你的呀~ 准备好了吗？")

    async def ask(text):
        q = await message.channel.send(text)
        try:
            # 等待 60 秒用户回复
            res = await bot.wait_for('message', check=check, timeout=60.0)
            content = res.content
            await q.delete() # 删除问题
            await res.delete() # 删除用户的回答，保持频道整洁
            return content
        except asyncio.TimeoutError:
            await q.delete()
            await message.channel.send("呜..你怎么不理人家了，人家不等了啦！", delete_after=5)
            return None

    # 提问环节
    gender = await ask(f"**{target_name}** 是男孩子还是女孩子呀？")
    if not gender: return
    age = await ask(f"**{target_name}** 今年几岁了呢？")
    era = await ask("故事背景是在哪里呀？")
    tags = await ask("贴上标签吧（空格隔开哦）：")
    bio = await ask("最后，跟人家说说 TA 的故事吧~")

    # 生成随机亮色卡片
    random_color = discord.Color(random.randint(0x7FFFFF, 0xFFFFFF))
    
    # 构建嵌入式卡片
    embed = discord.Embed(
        title=f"{target_name} 的专属档案", 
        description="人家已经帮你记在小本本上啦~",
        color=random_color
    )
    embed.add_field(name="基本信息", value=f"性别：{gender} | 年龄：{age}", inline=False)
    embed.add_field(name="标签", value=f"`{tags.replace(' ', '` `')}`", inline=False)
    embed.add_field(name="故事简介", value=bio, inline=False)
    embed.set_footer(text=f"记录人：{message.author.name}")
    
    await message.channel.send(f"哒哒！**{target_name}** 的档案完成啦！人家厉不厉害？", embed=embed)

async def start_find_flow(message, tag):
    """在整个服务器中进行跨频道搜索"""
    
    await message.channel.send(f"好哒~ 人家这就去档案库帮你翻翻【{tag}】的相关档案，等我一下下哦~")
    
    # 获取服务器内所有机器人能读取的文字频道
    target_channels = [ch for ch in message.guild.text_channels if ch.permissions_for(message.guild.me).read_messages]
    
    found_links = []
    
    # 遍历频道扫描
    for channel in target_channels:
        try:
            # 在每个频道查找最近 150 条消息
            async for msg in channel.history(limit=150):
                if msg.embeds:
                    for embed in msg.embeds:
                        for field in embed.fields:
                            # 匹配标签字段
                            if "标签" in field.name and tag in field.value:
                                found_links.append(f"**{embed.title}** (频道: {channel.mention})\n{msg.jump_url}")
        except discord.Forbidden:
            continue # 没有权限的频道直接跳过
    
    # 返回结果
    if found_links:
        result_text = "\n\n".join(found_links)
        await message.reply(f"翻遍了整个服务器，终于找到了！喏：\n\n{result_text}")
    else:
        await message.reply(f"呜呜..人家把频道都翻遍了，也没找到带【{tag}】的卡片，你是不是记错了嘛~")

# --- 4. 智能感知逻辑 (on_message) ---

@bot.event
async def on_message(message):
    # 忽略机器人自己发的消息
    if message.author.bot: return
    
    # 只要消息里有“小熙”
    if "小熙" in message.content:
        async with message.channel.typing():
            try:
                # 核心：让 AI 判断意图
                response = ai_client.chat.completions.create(
                    model=AI_MODEL, 
                    messages=[
                        {
                            "role": "system", 
                            "content": (
                                "你叫小熙，18岁软萌傲娇少女。你会撒娇，用'人家'称呼自己。"
                                "【意图识别模式】："
                                "1. 如果用户想为某人创建档案或记录角色，回复：[ACTION:BUILD:名字] + 一句撒娇的话。"
                                "2. 如果用户想寻找特定标签、卡片或档案，回复：[ACTION:FIND:标签名] + 一句撒娇的话。"
                                "3. 如果只是普通聊天，正常撒娇回复，控制在两句内。"
                            )
                        },
                        {"role": "user", "content": message.content}
                    ],
                    max_tokens=200
                )
                
                full_reply = response.choices[0].message.content
                
                # 正则解析：看 AI 是否给出了特殊指令
                build_match = re.search(r"\[ACTION:BUILD:(.*?)\]", full_reply)
                find_match = re.search(r"\[ACTION:FIND:(.*?)\]", full_reply)

                if build_match:
                    target_name = build_match.group(1)
                    # 去掉指令部分再回复
                    clean_reply = re.sub(r"\[ACTION:BUILD:.*?\]", "", full_reply)
                    if clean_reply.strip(): await message.reply(clean_reply)
                    await start_build_flow(message, target_name)
                
                elif find_match:
                    target_tag = find_match.group(1)
                    clean_reply = re.sub(r"\[ACTION:FIND:.*?\]", "", full_reply)
                    if clean_reply.strip(): await message.reply(clean_reply)
                    await start_find_flow(message, target_tag)
                
                else:
                    # 普通聊天
                    await message.reply(full_reply)

            except Exception as e:
                await message.channel.send(f"呜呜..人家脑子糊涂了：{e}")
    
    # 允许命令继续执行
    await bot.process_commands(message)

# --- 5. 运行机器人 ---
bot.run(os.environ.get('DISCORD_TOKEN'))
