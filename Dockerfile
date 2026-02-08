# 使用轻量级的 Python 镜像
FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 将当前目录下的文件复制到工作目录
COPY . .

# 安装依赖 (如果你有 requirements.txt)
RUN pip install -r requirements.txt

# 运行机器人
CMD ["python", "bot.py"]
