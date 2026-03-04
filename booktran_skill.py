"""
booktran Skill - nanobot 集成入口
提供 @booktran 命令支持
"""

import asyncio
from pathlib import Path
from typing import Optional

from workflow import TranslationWorkflow


class BooktranSkill:
    """booktran Skill for nanobot"""
    
    def __init__(self, workspace_dir: str):
        self.workspace_dir = Path(workspace_dir)
        self.config_path = self.workspace_dir / "config.yaml"
        self.output_dir = self.workspace_dir / "output"
    
    async def handle_command(self, command: str, args: list, context: dict) -> str:
        """处理 booktran 命令
        
        Args:
            command: 命令名 (translate/config/status/help)
            args: 命令参数
            context: 上下文信息 (user_id, chat_id, files 等)
        
        Returns:
            回复消息
        """
        
        if command == "help":
            return self._help_message()
        
        elif command == "config":
            return await self._cmd_config()
        
        elif command == "translate":
            return await self._cmd_translate(args, context)
        
        elif command == "status":
            return await self._cmd_status()
        
        else:
            return "❌ 未知命令。使用 `@booktran help` 查看帮助。"
    
    def _help_message(self) -> str:
        """帮助信息"""
        return """📚 **booktran - 文档翻译工具**

**命令列表**:
- `@booktran translate <文件>` - 翻译文件
- `@booktran config` - 修改配置
- `@booktran status` - 查看任务状态
- `@booktran help` - 帮助信息

**支持格式**:
PDF, EPUB, FB2, TXT, DOCX, HTML

**使用方法**:
1. 发送文件给我
2. 或命令：`@booktran translate book.pdf`
3. 等待翻译完成

**注意**: 首次使用请先配置 API。
"""
    
    async def _cmd_config(self) -> str:
        """配置命令"""
        # 检查是否已有配置
        if self.config_path.exists():
            msg = """⚙️ **当前配置**

配置文件：`config.yaml`

如需修改配置，请直接编辑 `config.yaml` 文件。
"""
            return msg
        else:
            # 首次配置
            return """🔧 **首次使用配置**

1. 复制配置模板：
```bash
cp config.yaml.template config.yaml
```

2. 编辑 `config.yaml`，填写你的 API 配置：
- `base_url`: API 地址
- `api_key`: 你的 API Key
- `model`: 模型名称

3. 配置完成后，使用 `@booktran translate <文件>` 开始翻译。
"""
    
    async def _cmd_translate(self, args: list, context: dict) -> str:
        """翻译命令"""
        
        # 检查配置
        if not self.config_path.exists():
            return "❌ 未配置！请先运行 `@booktran config`"
        
        # 获取文件
        file_path = None
        if args:
            # 从参数获取文件路径
            file_path = args[0]
        elif context.get("files"):
            # 从附件获取文件
            file_path = context["files"][0]
        
        if not file_path:
            return "❌ 请提供文件：\n`@booktran translate book.pdf`"
        
        # 检查文件是否存在
        if not Path(file_path).exists():
            return f"❌ 文件不存在：{file_path}"
        
        # 开始翻译
        try:
            workflow = TranslationWorkflow(
                config_path=str(self.config_path),
                workspace_dir=str(self.workspace_dir)
            )
            
            # 进度回调
            async def progress_callback(msg: str):
                # 这里可以发送进度消息给用户
                print(f"[进度] {msg}")
            
            result = await workflow.run(file_path, progress_callback)
            
            return f"✅ **翻译完成！**\n\n输出文件：`{result}`\n\n可以在 `output/` 目录找到翻译后的 EPUB 文件。"
        
        except Exception as e:
            return f"❌ **翻译失败**\n\n错误：{str(e)}\n\n请检查配置和文件格式。"
    
    async def _cmd_status(self) -> str:
        """状态命令"""
        from modules.state_manager import StateManager
        import json
        
        # 查找最近的任务状态
        state_files = list(self.output_dir.glob("state_*.json"))
        
        if not state_files:
            return "📊 **无进行中的任务**"
        
        # 读取最新的状态
        latest_state = sorted(state_files)[-1]
        state = json.loads(latest_state.read_text(encoding='utf-8'))
        
        progress = state.get("progress", 0)
        status = state.get("status", "unknown")
        current = state.get("current_chunk", 0)
        total = state.get("total_chunks", 0)
        
        status_emoji = {"running": "🔄", "completed": "✅", "error": "❌"}.get(status, "❓")
        
        return f"""📊 **任务状态**

状态：{status_emoji} {status}
进度：{progress}%
切片：{current}/{total}
任务 ID: `{state.get('task_id', 'N/A')}`

输出目录：`{latest_state.parent}`
"""


# nanobot Skill 入口
async def handle_message(message: dict) -> dict:
    """nanobot 消息处理入口
    
    Args:
        message: nanobot 消息格式
    
    Returns:
        回复消息格式
    """
    workspace_dir = Path(__file__).parent
    skill = BooktranSkill(str(workspace_dir))
    
    # 解析命令
    content = message.get("content", "")
    if not content.startswith("@booktran"):
        return {"reply": ""}
    
    # 提取命令
    parts = content.replace("@booktran", "").strip().split()
    if not parts:
        return {"reply": "❌ 请提供命令。使用 `@booktran help` 查看帮助。"}
    
    command = parts[0]
    args = parts[1:] if len(parts) > 1 else []
    
    # 上下文
    context = {
        "user_id": message.get("from_id"),
        "chat_id": message.get("chat_id"),
        "files": message.get("attachments", [])
    }
    
    # 处理命令
    reply = await skill.handle_command(command, args, context)
    
    return {"reply": reply}


# 测试入口
if __name__ == "__main__":
    # 简单测试
    skill = BooktranSkill(str(Path(__file__).parent))
    
    async def test():
        reply = await skill.handle_command("help", [], {})
        print(reply)
    
    asyncio.run(test())
