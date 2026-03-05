#!/usr/bin/env python3
"""启动翻译任务"""

import asyncio
import sys
from pathlib import Path

# 添加路径
sys.path.insert(0, str(Path(__file__).parent))

from workflow import TranslationWorkflow


def print_progress(msg):
    """打印进度"""
    print(msg)


async def main():
    # 配置
    config_path = Path(__file__).parent / "config.yaml"
    workspace_dir = Path(__file__).parent
    input_file = workspace_dir / "input" / "new_book.epub"
    
    if not input_file.exists():
        print(f"❌ 文件不存在：{input_file}")
        return
    
    # 创建工作流
    workflow = TranslationWorkflow(
        config_path=str(config_path),
        workspace_dir=str(workspace_dir)
    )
    
    # 运行翻译
    try:
        output_path = await workflow.run(
            file_path=str(input_file),
            progress_callback=print_progress
        )
        print(f"\n✅ 翻译完成！输出：{output_path}")
    except Exception as e:
        print(f"\n❌ 翻译失败：{e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())
