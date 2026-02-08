import discord
from discord.ext import commands
import os
import openai # 确保 requirements.txt 里有 openai
import asyncio
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- AI 配置 (在 bot.run 之前) ---
# 从环境变量读取配置，确保 Zeabur 里都设置了这三个变量
openai.api_key = os.environ['AI_API_KEY']
openai.base_url = os.environ['AI_BASE_URL'] # 你的自定义兼容地址
AI_MODEL = os.environ['AI_MODEL']          # 这里填 gemini-3-flash 或类似的

@bot.command()
async def build(ctx):
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    # 1. 删除 !build 命令
    try: await ctx.message.delete()
    except: pass

    # --- 提问与回答函数 ---
    async def ask_and_delete(question_text):
        q_msg = await ctx.send(question_text)                
        response = await bot.wait_for('message', check=check)
        
        # 删除问题和回答
        try:
            await q_msg.delete()
            await response.delete()
        except:
            pass
            
        return response.content

    # --- 依次提问 ---                
    name = await ask_and_delete("1. 角色**姓名**？")
    gender = await ask_and_delete("2. 角色**性别**？")
    age = await ask_and_delete("3. 角色**年龄**？")
    era = await ask_and_delete("4. 角色**年代**？")
    tags = await ask_and_delete("5. 角色**标签**？(用空格隔开)")
    bio = await ask_and_delete("6. 角色**简介**？")

    # --- 自动处理时间 ---
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # --- 生成最终结果 (结构化排版) ---                
    embed = discord.Embed(
        title=f"👤 {name}",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="性别", value=gender, inline=True)
    embed.add_field(name="年龄", value=age, inline=True)
    embed.add_field(name="年代", value=era, inline=True)
    embed.add_field(name="标签", value=f"`{tags.replace(' ', '` `')}`", inline=False)
    embed.add_field(name="简介", value=bio, inline=False)
    
    embed.set_footer(text=f"登记人: {ctx.author.name} | 登记时间: {now}")

    await ctx.send(f"档案已登记: **{name}**", embed=embed)

@bot.command()
async def chat(ctx, *, message):
    """跟 Gemini AI 对话的命令"""
    async with ctx.typing():
        try:
            # 调用 AI 接口 (使用新版本的语法)
            response = openai.chat.completions.create(
                model=AI_MODEL, 
                messages=[
                    {"role": "system", "content": "你是一个女生，你的年龄在18岁，你的性格是傲娇、毒舌，对于我们提出的问题，你会用三分傲七分娇的语气回答，你会骂我们笨蛋，但是你不会用侮辱的词汇，面对不合理的不礼貌的话你需要拒绝，你是一个独立的人格。"},
                    {"role": "user", "content": message}
                ]
            )
            # 获取 AI 的回复
            ai_reply = response.choices[0].message.content
            await ctx.send(ai_reply)
        except Exception as e:
            await ctx.send(f"哎呀，AI 好像睡着了：{e}")

# --- 登录 (放在最末尾) ---
bot.run(os.environ['DISCORD_TOKEN'])
