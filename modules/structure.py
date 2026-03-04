"""
文档结构保存模块 - 保存完整的原文档结构信息
用于在合并翻译时准确复原章节、图片位置、目录等
"""

import json
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime


@dataclass
class PageInfo:
    """页面信息（用于 PDF 或分页文档）"""
    page_num: int           # 页码（从 1 开始）
    start_char: int         # 在全文本中的起始字符位置
    end_char: int           # 在全文本中的结束字符位置
    chapter_id: int         # 所属章节 ID


@dataclass
class ImageLocation:
    """图片位置信息"""
    image_id: int           # 图片 ID
    image_href: str         # 图片原始路径
    chapter_id: int         # 所属章节 ID
    position_in_chapter: int  # 在章节内的位置（第几个元素）
    page_num: int = 0       # 所在页码（如果有）
    before_text: str = ""   # 图片前的文本（前 100 字符）
    after_text: str = ""    # 图片后的文本（后 100 字符）


@dataclass
class ChapterStructure:
    """章节结构信息"""
    id: int
    title: str              # 原始章节标题
    start_pos: int          # 在全文本中的起始位置
    end_pos: int            # 在全文本中的结束位置
    title_level: int = 1    # 标题级别（h1=1, h2=2, ...）
    start_page: int = 0     # 起始页码
    end_page: int = 0       # 结束页码
    image_ids: List[int] = field(default_factory=list)  # 包含的图片 ID 列表
    word_count: int = 0     # 字数统计
    parent_id: int = -1     # 父章节 ID（用于层级结构）
    children_ids: List[int] = field(default_factory=list)  # 子章节 ID 列表


@dataclass
class TableOfContents:
    """目录结构"""
    title: str
    level: int              # 层级（1=一级目录，2=二级目录...）
    chapter_id: int         # 对应的章节 ID
    page_num: int = 0       # 页码
    children: List['TableOfContents'] = field(default_factory=list)


@dataclass
class DocumentStructure:
    """完整文档结构"""
    # 基本信息
    source_file: str                    # 原始文件名
    source_type: str                    # 文档类型（pdf/epub/...）
    title: str                          # 书名
    language: str = "en"                # 原始语言
    total_chars: int = 0                # 总字符数
    total_pages: int = 0                # 总页数（如果有）
    
    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)
    # {author, publisher, isbn, publication_date, ...}
    
    # 结构信息
    chapters: List[ChapterStructure] = field(default_factory=list)
    images: List[Dict[str, Any]] = field(default_factory=list)
    # 每张图片：{id, href, path, media_type, size, location: ImageLocation}
    
    # 目录（可选，如果有独立目录）
    toc: List[TableOfContents] = field(default_factory=list)
    
    # 页码映射（可选，用于 PDF）
    pages: List[PageInfo] = field(default_factory=list)
    
    # 翻译范围（用于指定页数）
    translation_range: Dict[str, int] = field(default_factory=dict)
    # {start_page, end_page, start_chapter, end_chapter, start_char, end_char}
    
    # 生成时间
    created_at: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """转换为字典（用于 JSON 序列化）"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'DocumentStructure':
        """从字典创建"""
        return cls(**data)


class StructureManager:
    """结构管理器 - 保存和加载文档结构"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.structure_file = self.output_dir / 'doc_structure.json'
    
    def save_structure(self, structure: DocumentStructure):
        """保存结构到文件"""
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(self.structure_file, 'w', encoding='utf-8') as f:
            json.dump(structure.to_dict(), f, ensure_ascii=False, indent=2)
        
        print(f"✅ 文档结构已保存：{self.structure_file}")
    
    def load_structure(self) -> DocumentStructure:
        """从文件加载结构"""
        if not self.structure_file.exists():
            raise FileNotFoundError(f"结构文件不存在：{self.structure_file}")
        
        with open(self.structure_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 手动转换嵌套的 dataclass
        structure = self._dict_to_structure(data)
        print(f"✅ 文档结构已加载：{self.structure_file}")
        print(f"   章节数：{len(structure.chapters)}")
        print(f"   图片数：{len(structure.images)}")
        print(f"   总字符：{structure.total_chars:,}")
        
        return structure
    
    def _dict_to_structure(self, data: Dict) -> DocumentStructure:
        """递归将字典转换为 DocumentStructure"""
        # 转换章节
        chapters = []
        for ch_data in data.get('chapters', []):
            ch = ChapterStructure(**ch_data)
            chapters.append(ch)
        
        # 创建结构对象
        structure = DocumentStructure(
            source_file=data.get('source_file', ''),
            source_type=data.get('source_type', ''),
            title=data.get('title', ''),
            language=data.get('language', 'en'),
            total_chars=data.get('total_chars', 0),
            total_pages=data.get('total_pages', 0),
            metadata=data.get('metadata', {}),
            chapters=chapters,
            images=data.get('images', []),
            toc=data.get('toc', []),
            pages=data.get('pages', []),
            translation_range=data.get('translation_range', {}),
            created_at=data.get('created_at', '')
        )
        
        return structure
    
    def set_translation_range(self, start_page: int = None, end_page: int = None,
                             start_chapter: int = None, end_chapter: int = None):
        """设置翻译范围（在解析后调用）"""
        structure = self.load_structure()
        
        structure.translation_range = {}
        
        if start_page is not None:
            structure.translation_range['start_page'] = start_page
        if end_page is not None:
            structure.translation_range['end_page'] = end_page
        if start_chapter is not None:
            structure.translation_range['start_chapter'] = start_chapter
        if end_chapter is not None:
            structure.translation_range['end_chapter'] = end_chapter
        
        self.save_structure(structure)
        print(f"✅ 翻译范围已设置：{structure.translation_range}")


def create_structure_from_document(doc, output_dir: str) -> DocumentStructure:
    """从解析后的 Document 对象创建结构"""
    
    # 创建结构对象
    structure = DocumentStructure(
        source_file=doc.original_path,
        source_type=doc.source_type,
        title=doc.title,
        language=doc.metadata.get('language', 'en'),
        total_chars=doc.metadata.get('total_chars', 0),
        total_pages=doc.metadata.get('total_pages', 0),
        metadata=doc.metadata.copy()
    )
    
    # 转换章节
    for chapter in doc.chapters:
        ch_struct = ChapterStructure(
            id=chapter.id,
            title=chapter.title,
            start_pos=chapter.start_pos,
            end_pos=chapter.end_pos,
            word_count=len(chapter.text),
            image_ids=[i for i, img in enumerate(doc.images) 
                      if img in chapter.images]
        )
        structure.chapters.append(ch_struct)
    
    # 转换图片（添加位置信息）
    for img_id, img in enumerate(doc.images):
        img_info = img.copy()
        img_info['id'] = img_id
        
        # 查找图片位置
        for chapter in doc.chapters:
            if img in chapter.images:
                # 估算图片在章节中的位置
                img_info['location'] = {
                    'chapter_id': chapter.id,
                    'position_in_chapter': chapter.images.index(img)
                }
                break
        
        structure.images.append(img_info)
    
    return structure


def filter_chunks_by_range(chunks, structure: DocumentStructure, 
                           start_page: int = None, end_page: int = None,
                           start_chapter: int = None, end_chapter: int = None):
    """根据范围过滤切片"""
    
    if not structure.translation_range and not any([start_page, end_page, start_chapter, end_chapter]):
        # 没有范围限制，返回全部
        return chunks
    
    # 确定范围
    range_info = structure.translation_range if structure.translation_range else {}
    start_p = start_page or range_info.get('start_page', 0)
    end_p = end_page or range_info.get('end_page', float('inf'))
    start_ch = start_chapter or range_info.get('start_chapter', 0)
    end_ch = end_chapter or range_info.get('end_chapter', float('inf'))
    
    filtered = []
    for chunk in chunks:
        # 检查章节范围
        if start_ch <= chunk.chapter_id <= end_ch:
            filtered.append(chunk)
        # 检查页码范围（如果有页码信息）
        elif hasattr(chunk, 'page_num') and start_p <= chunk.page_num <= end_p:
            filtered.append(chunk)
    
    print(f"📝 切片过滤：{len(chunks)} → {len(filtered)} (章节 {start_ch}-{end_ch}, 页码 {start_p}-{end_p})")
    return filtered
