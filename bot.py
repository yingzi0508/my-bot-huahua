import discord
from discord.ext import commands
import os
from openai import OpenAI  # 确保 requirements.txt 里的 openai 版本是 1.0.0+
import asyncio
from datetime import datetime

# --- 基础配置 ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# --- AI 客户端初始化 (关键修改) ---
# 这样写可以确保 API 密钥和地址被正确识别
ai_client = OpenAI(
    api_key=os.environ.get('AI_API_KEY'),
    base_url=os.environ.get('AI_BASE_URL')  # 记得在 Zeabur 变量里结尾加上 /v1
)
AI_MODEL = os.environ.get('AI_MODEL')

@bot.event
async def on_ready():
    print(f'机器人已上线: {bot.user.name}')

@bot.command()
async def build(ctx):
    """档案登记命令"""
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    # 1. 删除触发命令的消息
    try: 
        await ctx.message.delete()
    except: 
        pass

    async def ask_and_delete(question_text):
        q_msg = await ctx.send(question_text)                
        try:
            # 等待用户回答，超时时间 60 秒
            response = await bot.wait_for('message', check=check, timeout=60.0)
            content = response.content
            await q_msg.delete()
            await response.delete()
            return content
        except asyncio.TimeoutError:
            await q_msg.delete()
            await ctx.send("回答超时，登记已取消。", delete_after=5)
            return None

    # --- 依次提问 ---                
    name = await ask_and_delete("1. 角色**姓名**？")
    if not name: return
    
    gender = await ask_and_delete("2. 角色**性别**？")
    if not gender: return
    
    age = await ask_and_delete("3. 角色**年龄**？")
    if not age: return
    
    era = await ask_and_delete("4. 角色**年代**？")
    if not era: return
    
    tags = await ask_and_delete("5. 角色**标签**？(用空格隔开)")
    if not tags: return
    
    bio = await ask_and_delete("6. 角色**简介**？")
    if not bio: return

    # --- 生成最终结果 ---                
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
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
    """跟傲娇 AI 对话的命令"""
    async with ctx.typing():
        try:
            # 调用 AI 接口
            response = ai_client.chat.completions.create(
                model=AI_MODEL, 
                messages=[
                    {
                        "role": "system", 
                        "content": "你是一个女生，你的年龄在18岁，你的性格是傲娇、毒舌，对于我们提出的问题，你会用三分傲七分娇的语气回答，你会骂我们笨蛋，但是你不会用侮辱的词汇，面对不合理的不礼貌的话你需要拒绝，你是一个独立的人格。"
                    },
                    {"role": "user", "content": message}
                ]
            )
            # 获取并发送 AI 的回复
            ai_reply = response.choices[0].message.content
            await ctx.send(ai_reply)
        except Exception as e:
            # 这里的报错会更详细，方便排查
            await ctx.send(f"哼，笨蛋！代码出错了，快去检查：\n`{str(e)}`")

# --- 运行机器人 ---
bot.run(os.environ.get('DISCORD_TOKEN'))
