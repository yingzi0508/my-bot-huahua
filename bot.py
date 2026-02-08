import discord
from discord import app_commands  # 用于斜杠指令
from discord.ext import commands
import os
from openai import OpenAI
import asyncio
from datetime import datetime
import random  # 引入随机数库，用于随机颜色

# --- 1. 基础配置与权限 ---
# Intents 是机器人的感知权限，必须开启 message_content 才能听到“小熙”
intents = discord.Intents.default()
intents.message_content = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# --- 2. AI 客户端初始化 ---
ai_client = OpenAI(
    api_key=os.environ.get('AI_API_KEY'),
    base_url=os.environ.get('AI_BASE_URL') # Zeabur 变量建议以 /v1 结尾
)
AI_MODEL = os.environ.get('AI_MODEL')

# --- 3. 机器人启动事件 ---
@bot.event
async def on_ready():
    # 同步斜杠指令到 Discord 服务器
    try:
        synced = await bot.tree.sync()
        print(f"已同步 {len(synced)} 个斜杠指令")
    except Exception as e:
        print(f"同步指令失败: {e}")
    print(f'✨ 小熙已上线！当前身份：{bot.user.name}')

# --- 4. 关键词监听 (听到“小熙”就说话) ---
@bot.event
async def on_message(message):
    # 排除机器人自己的消息，防止无限循环
    if message.author.bot:
        return

    # 判断消息中是否包含“小熙”
    if "小熙" in message.content:
        async with message.channel.typing():
            try:
                response = ai_client.chat.completions.create(
                    model=AI_MODEL, 
                    messages=[
                        {
                            "role": "system", 
                            "content": (
                                "你叫小熙，是一个18岁的傲娇毒舌女生。"
                                "语气：三分傲七分娇，会骂用户笨蛋，但心不坏。"
                                "要求：你的回答必须简短精炼（控制在两句话以内），适合日常闲聊，不要啰嗦。"
                                "原则：独立人格，拒绝不礼貌请求。"
                            )
                        },
                        {"role": "user", "content": message.content}
                    ],
                    max_tokens=150 # 限制 AI 回复的最大字数，双重保险
                )
                ai_reply = response.choices[0].message.content
                await message.reply(ai_reply) # 使用 reply 会艾特用户，更有互动感
            except Exception as e:
                await message.channel.send(f"哼，笨蛋！连接断掉了啦：{e}")

    # 必须加上这一行，否则传统的插件指令（如果有的话）会失效
    await bot.process_commands(message)

# --- 5. 斜杠指令：登记档案 (/build) ---
@bot.tree.command(name="build", description="开始登记你的角色档案")
async def build(interaction: discord.Interaction):
    """
    使用斜杠指令触发。
    注意：斜杠指令使用 interaction 而不是 ctx。
    """
    
    # 定义检查函数，确保只听取触发指令的那个人的回答
    def check(m):
        return m.author == interaction.user and m.channel == interaction.channel

    # 第一次回应（斜杠指令必须在 3 秒内做出响应）
    await interaction.response.send_message("既然你求我，那我就勉强帮你登记一下吧！笨蛋！", ephemeral=True)

    # 内部提问辅助函数
    async def ask_question(question_text):
        q_msg = await interaction.channel.send(question_text)                
        try:
            # 等待 60 秒
            response = await bot.wait_for('message', check=check, timeout=60.0)
            content = response.content
            await q_msg.delete()    # 删除问题
            await response.delete() # 删除用户的回答，保持频道整洁
            return content
        except asyncio.TimeoutError:
            await q_msg.delete()
            await interaction.channel.send("笨蛋，动作太慢了！登记取消！", delete_after=5)
            return None

    # 依次询问
    name = await ask_question("1. 角色**姓名**叫什么？")
    if not name: return
    gender = await ask_question(f"2. **{name}** 的性别是？")
    if not gender: return
    age = await ask_question(f"3. **{name}** 今年几岁了？")
    if not age: return
    era = await ask_question("4. 故事发生在什么**年代**？")
    if not era: return
    tags = await ask_question("5. 给角色贴点**标签**吧（空格隔开）：")
    if not tags: return
    bio = await ask_question("6. 最后，简单介绍一下这个角色：")
    if not bio: return

    # --- 生成随机颜色的卡片 ---
    random_color = discord.Color(random.randint(0, 0xFFFFFF)) # 生成完全随机的颜色
    
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    # 构建嵌入式卡片
    embed = discord.Embed(
        title=f" 角色档案：{name}",
        description="这份档案已经安全存入数据库了（大概）。",
        color=random_color
    )
    
    embed.add_field(name="基本信息", value=f"性别：{gender} | 年龄：{age}", inline=False)
    embed.add_field(name="年代背景", value=era, inline=True)
    embed.add_field(name="个性标签", value=f"`{tags.replace(' ', '` `')}`", inline=False)
    embed.add_field(name="人物小传", value=bio, inline=False)
    
    # 底部页脚
    embed.set_footer(text=f"登记人: {interaction.user.name} | 时间: {now}")

    # 在频道发出最终卡片
    await interaction.channel.send(f"✅ **{name}** 的档案已生成！", embed=embed)

# --- 6. 运行机器人 ---
# 使用 get 方式获取环境变量，防止报错
TOKEN = os.environ.get('DISCORD_TOKEN')
if TOKEN:
    bot.run(TOKEN)
else:
    print("错误：未找到 DISCORD_TOKEN 环境变量！")