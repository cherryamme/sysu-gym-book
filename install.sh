#!/bin/bash

echo "正在安装中山大学体育馆预约脚本..."

# 检查Python版本
python_version=$(python3 --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+')
if [ -z "$python_version" ]; then
    echo "错误: 未找到Python3，请先安装Python3"
    exit 1
fi

echo "检测到Python版本: $python_version"

# 安装依赖
echo "正在安装Python依赖包..."
pip3 install -r requirements.txt

# 安装Playwright浏览器
echo "正在安装Playwright浏览器..."
python3 -m playwright install chromium

echo "安装完成！"
echo ""
echo "使用方法："
echo "1. 创建 .env 文件并配置你的账号信息："
echo "   cp .env.example .env"
echo "   # 编辑 .env 文件，填入你的用户名和密码"
echo ""
echo "2. 运行预约脚本："
echo "   python3 gym_booking.py --username 你的用户名 --password 你的密码"
echo ""
echo "3. 调试模式（显示浏览器窗口）："
echo "   python3 gym_booking.py --username 你的用户名 --password 你的密码 --debug"
echo ""
echo "更多参数请使用 --help 查看"
