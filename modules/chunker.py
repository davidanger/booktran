"""
智能切片模块 - 按章节边界和完整句子切割
"""

from typing import List, Dict
from dataclasses import dataclass
import re


@dataclass
class Chunk:
    """切片数据"""
    id: int
    text: str
    chapter_id: int       # 所属章节 ID
    chapter_title: str    # 章节标题（原文）
    chunk_index: int      # 在章节内的索引
    total_chunks: int     # 章节内总切片数
    start_pos: int        # 在章节内的起始位置
    end_pos: int          # 在章节内的结束位置
    chapter_title_translated: str = ""  # 章节标题（翻译后）
    is_first: bool = False   # 是否是章节的第一片
    is_last: bool = False    # 是否是章节的最后一片
    has_chapter_title: bool = False  # 是否包含章节标题


class Chunker:
    """智能切片器 - 按章节边界和完整句子切割"""
    
    def __init__(self, max_chars: int = 8000, overlap: int = 0):
        """
        Args:
            max_chars: 每片最大字符数
            overlap: 重叠字符数（始终为 0，不做衔接覆盖）
        """
        self.max_chars = max_chars
        self.overlap = 0  # 强制设为 0，不做重叠
    
    def split(self, chapters: List[Dict]) -> List[Chunk]:
        """
        将文档按章节切割
        
        Args:
            chapters: 章节列表，每项包含：
                - id: 章节 ID
                - title: 章节标题
                - text: 章节纯文本
        
        Returns:
            切片列表
        """
        result = []
        chunk_id = 0
        
        for chapter in chapters:
            chapter_id = chapter.get('id', 0)
            chapter_title = chapter.get('title', f'第{chapter_id + 1}章')
            text = chapter.get('text', '')
            
            if not text.strip():
                continue
            
            # 如果章节长度 <= max_chars，作为一片
            if len(text) <= self.max_chars:
                chunk = Chunk(
                    id=chunk_id,
                    text=text,
                    chapter_id=chapter_id,
                    chapter_title=chapter_title,
                    chunk_index=0,
                    total_chunks=1,
                    start_pos=0,
                    end_pos=len(text),
                    is_first=True,
                    is_last=True,
                    has_chapter_title=True
                )
                result.append(chunk)
                chunk_id += 1
            else:
                # 章节太长，需要细分
                chapter_chunks = self._split_chapter(
                    text, chapter_id, chapter_title, chunk_id
                )
                
                # 标记首尾
                if chapter_chunks:
                    chapter_chunks[0].is_first = True
                    chapter_chunks[0].has_chapter_title = True
                    chapter_chunks[-1].is_last = True
                
                result.extend(chapter_chunks)
                chunk_id += len(chapter_chunks)
        
        return result
    
    def _split_chapter(self, text: str, chapter_id: int, chapter_title: str, 
                       start_id: int) -> List[Chunk]:
        """
        将单个章节细分为多个切片
        
        策略：
        1. 优先在段落边界切割（\n\n）
        2. 其次在句子边界切割（。！？.!?）
        3. 避免在词语中间切断
        4. 不做重叠覆盖
        """
        chunks = []
        pos = 0
        chunk_index = 0
        
        while pos < len(text):
            # 计算目标结束位置
            target_end = pos + self.max_chars
            
            # 如果已到达末尾，直接取剩余部分
            if target_end >= len(text):
                chunk_text = text[pos:]
                chunks.append(Chunk(
                    id=start_id + len(chunks),
                    text=chunk_text,
                    chapter_id=chapter_id,
                    chapter_title=chapter_title,
                    chunk_index=chunk_index,
                    total_chunks=0,  # 稍后统一计算
                    start_pos=pos,
                    end_pos=len(text),
                    is_first=(chunk_index == 0),
                    is_last=True,
                    has_chapter_title=(chunk_index == 0)
                ))
                break
            
            # 寻找最佳切割点（完整句子边界）
            cut_pos = self._find_sentence_boundary(text, pos, target_end)
            
            # 提取切片
            chunk_text = text[pos:cut_pos]
            
            chunks.append(Chunk(
                id=start_id + len(chunks),
                text=chunk_text,
                chapter_id=chapter_id,
                chapter_title=chapter_title,
                chunk_index=chunk_index,
                total_chunks=0,
                start_pos=pos,
                end_pos=cut_pos,
                is_first=(chunk_index == 0),
                is_last=False,
                has_chapter_title=(chunk_index == 0)
            ))
            
            # 移动到下一片（不做重叠）
            pos = cut_pos
            chunk_index += 1
        
        # 更新 total_chunks
        total = len(chunks)
        for i, chunk in enumerate(chunks):
            chunk.total_chunks = total
            chunk.chunk_index = i
            chunk.is_last = (i == total - 1)
        
        return chunks
    
    def _find_sentence_boundary(self, text: str, start: int, target_end: int) -> int:
        """
        寻找最佳句子边界切割点
        
        优先级：
        1. 段落边界（\n\n）
        2. 句子结束标点（。！？.!?）
        3. 分句标点（，；：,;:）
        4. 空格
        5. 强制切割（最后手段）
        """
        # 最小切片大小（避免切片过小）
        min_size = self.max_chars // 4
        
        # 搜索范围：从目标位置往回找
        search_start = max(start, target_end - self.max_chars // 2)
        search_end = target_end
        
        # 1. 段落边界
        for sep in ['\n\n', '\n\r\n', '\r\n\r\n']:
            idx = text.rfind(sep, search_start, search_end)
            if idx > start + min_size:
                return idx + len(sep)
        
        # 2. 句子结束标点（中文）
        for sep in ['。”', '！”', '？”', '。”\n', '！”\n', '？”\n', '。', '！', '？']:
            idx = text.rfind(sep, search_start, search_end)
            if idx > start + min_size:
                return idx + len(sep)
        
        # 3. 句子结束标点（英文）
        for sep in ['."\n', '!"\n', '?"\n', '. ', '! ', '? ', '."', '!"', '?"']:
            idx = text.rfind(sep, search_start, search_end)
            if idx > start + min_size:
                return idx + len(sep)
        
        # 4. 分句标点
        for sep in ['，', '；', '：', ',', ';', ':', '、']:
            idx = text.rfind(sep, search_start, search_end)
            if idx > start + min_size:
                return idx + len(sep)
        
        # 5. 空格
        idx = text.rfind(' ', search_start, search_end)
        if idx > start + min_size:
            return idx + 1
        
        # 6. 强制切割（避免切断 UTF-8 多字节字符）
        for i in range(4):
            if target_end - i > start:
                return target_end - i
        
        return target_end


class ChunkMerger:
    """切片合并器 - 翻译后合并，不做去重（因为无重叠）"""
    
    def __init__(self, overlap: int = 0):
        self.overlap = 0  # 无重叠，无需去重
    
    def merge(self, translated_chunks: List[Chunk]) -> Dict[int, str]:
        """
        将翻译后的切片按章节合并
        
        Args:
            translated_chunks: 翻译后的切片列表
        
        Returns:
            {chapter_id: 完整章节文本}
        """
        # 按章节分组
        chapters = {}
        for chunk in translated_chunks:
            chapter_id = chunk.chapter_id
            if chapter_id not in chapters:
                chapters[chapter_id] = []
            chapters[chapter_id].append(chunk)
        
        # 合并每章
        result = {}
        for chapter_id, chunks in chapters.items():
            # 按 chunk_index 排序
            chunks.sort(key=lambda c: c.chunk_index)
            
            # 直接拼接（无重叠，无需去重）
            merged_text = "".join([c.text for c in chunks])
            result[chapter_id] = merged_text
        
        return result
