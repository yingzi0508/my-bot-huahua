import discord
from discord.ext import commands
import os
import asyncio
from datetime import datetime # 导入时间库

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

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

    # --- 依次提问 (对应你的结构) ---                
    name = await ask_and_delete("1. 角色**姓名**？")
    gender = await ask_and_delete("2. 角色**性别**？")
    age = await ask_and_delete("3. 角色**年龄**？")
    era = await ask_and_delete("4. 角色**年代**？")
    tags = await ask_and_delete("5. 角色**标签**？(用空格隔开)")
    bio = await ask_and_delete("6. 角色**简介**？")

    # --- 自动处理时间 ---
    # 获取当前日期时间，格式化为：年-月-日 时:分
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # --- 生成最终结果 (结构化排版) ---                
    embed = discord.Embed(
        title=f"👤 {name}",
        color=discord.Color.blue()
    )
    
    # 将属性整齐地放入字段中
    embed.add_field(name="性别", value=gender, inline=True)
    embed.add_field(name="年龄", value=age, inline=True)
    embed.add_field(name="年代", value=era, inline=True)
    embed.add_field(name="标签", value=f"`{tags.replace(' ', '` `')}`", inline=False) # 标签处理得更好看
    embed.add_field(name="简介", value=bio, inline=False)
    
    # 设置页脚，自动带上当前时间
    embed.set_footer(text=f"登记人: {ctx.author.name} | 登记时间: {now}")

    # 发送最终的卡片
    await ctx.send(f"档案已登记: **{name}**", embed=embed)

bot.run(os.environ['DISCORD_TOKEN'])
