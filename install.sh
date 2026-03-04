#!/bin/bash
# booktran 安装脚本

set -e

echo "📚 booktran 安装脚本"
echo "===================="
echo ""

# 检测 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未找到 Python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python 版本：$PYTHON_VERSION"

# 安装依赖
echo ""
echo "正在安装依赖..."
pip3 install -r requirements.txt

# 验证安装
echo ""
echo "验证安装..."
python3 -c "from modules.parser import parse_document; print('✓ 模块导入成功')"

# 提示配置
echo ""
echo "✅ 安装完成！"
echo ""
echo "下一步:"
echo "1. 复制配置模板：cp config.yaml.template config.yaml"
echo "2. 编辑配置：vim config.yaml (填写你的 API 配置)"
echo "3. 开始翻译：python3 booktran_skill.py input/book.epub"
echo ""
