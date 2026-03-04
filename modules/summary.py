"""
摘要管理模块 - 维护翻译摘要和术语表
"""

from pathlib import Path
from typing import Optional


class SummaryManager:
    """摘要管理器"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.summary_path = self.output_dir / "summary.md"
        self.terms_path = self.output_dir / "terms.md"
    
    async def load(self) -> str:
        """加载当前摘要"""
        if self.summary_path.exists():
            return self.summary_path.read_text(encoding='utf-8')
        return ""
    
    async def update(
        self,
        chunk_id: int,
        original_text: str,
        translated_text: str,
        auto_extract_terms: bool = True
    ):
        """更新摘要"""
        current_summary = await self.load()
        
        # 提取关键内容（简化版：取前 200 字）
        content_summary = self._summarize_content(translated_text, max_len=200)
        
        # 追加当前片核心内容
        new_entry = f"""
## 第{chunk_id}片
- 核心内容：{content_summary}
"""
        
        updated_summary = current_summary + new_entry
        self.summary_path.write_text(updated_summary, encoding='utf-8')
    
    def _summarize_content(self, text: str, max_len: int = 200) -> str:
        """提取内容摘要"""
        # 简化实现：取前 max_len 字
        return text[:max_len] + "..." if len(text) > max_len else text
    
    async def get_terms(self) -> str:
        """获取术语表"""
        if self.terms_path.exists():
            return self.terms_path.read_text(encoding='utf-8')
        return ""
