"""
状态管理模块 - 断点续传支持
"""

import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime


class StateManager:
    """状态管理器"""
    
    def __init__(self, output_dir: str, task_id: str):
        self.output_dir = Path(output_dir)
        self.state_path = self.output_dir / f"state_{task_id}.json"
        self.task_id = task_id
    
    async def save(
        self,
        current_chunk: int,
        total_chunks: int,
        status: str = "running"
    ):
        """保存状态"""
        state = {
            "task_id": self.task_id,
            "status": status,
            "current_chunk": current_chunk,
            "total_chunks": total_chunks,
            "progress": round(current_chunk / total_chunks * 100, 2) if total_chunks > 0 else 0,
            "last_updated": datetime.now().isoformat(),
            "completed_chunks": list(range(current_chunk))
        }
        
        self.state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8')
    
    async def load(self) -> Optional[Dict]:
        """加载状态"""
        if self.state_path.exists():
            return json.loads(self.state_path.read_text(encoding='utf-8'))
        return None
    
    async def resume(self) -> Optional[int]:
        """恢复任务，返回下一个要处理的 chunk_id"""
        state = await self.load()
        if state and state["status"] == "running":
            return state["current_chunk"]
        return None
    
    async def complete(self):
        """标记任务完成"""
        state = await self.load()
        if state:
            state["status"] = "completed"
            state["completed_at"] = datetime.now().isoformat()
            self.state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding='utf-8')
