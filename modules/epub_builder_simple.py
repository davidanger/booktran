"""
EPUB 构建模块 - 简化版
"""

from ebooklib import epub
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger('booktran.epub_builder')


class EPUBBuilder:
    """EPUB 构建器"""
    
    def __init__(self, output_dir: str, title: str, doc_chapters: List = None, doc_images: List = None):
        self.output_dir = Path(output_dir)
        self.title = title
        self.book = epub.EpubBook()
        self.doc_chapters = doc_chapters or []
        self.doc_images = doc_images or []
        
        # 设置 CSS
        self.css = epub.EpubItem(
            uid="style",
            file_name="style/main.css",
            media_type="text/css",
            content='''
body { font-family: "SimSun", serif; line-height: 1.8; margin: 1em; }
h1 { text-align: center; margin: 1.5em 0; page-break-after: avoid; }
p { text-indent: 2em; margin: 0.5em 0; }
img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
.chapter-title { font-size: 1.5em; font-weight: bold; text-align: center; margin: 2em 0 1em; page-break-before: always; }
'''
        )
        self.book.add_item(self.css)
    
    async def build(self, translated_chunks: List, summary: str) -> str:
        """构建 EPUB"""
        from modules.chunker import ChunkMerger
        
        # 设置元数据
        self.book.set_identifier(f"translated-{self.title}")
        self.book.set_title(f"{self.title} (中文翻译)")
        self.book.set_language("zh")
        
        # 合并翻译结果
        merger = ChunkMerger()
        chapter_texts = merger.merge(translated_chunks)
        
        logger.info(f"合并翻译结果：{len(chapter_texts)}章")
        
        # 添加章节
        epub_chapters = []
        for chapter_id, chapter_text in chapter_texts.items():
            # 查找章节标题
            chapter_title = f"第{chapter_id + 1}章"
            for doc_ch in self.doc_chapters:
                if isinstance(doc_ch, dict) and doc_ch.get('id') == chapter_id:
                    chapter_title = doc_ch.get('title', chapter_title)
                    break
                elif hasattr(doc_ch, 'id') and doc_ch.id == chapter_id:
                    chapter_title = doc_ch.title
                    break
            
            # 创建章节
            chapter = epub.EpubHtml(
                title=chapter_title,
                file_name=f"chapter_{chapter_id + 1}.xhtml",
                lang="zh",
                uid=f"chapter_{chapter_id + 1}"
            )
            
            # 生成 HTML
            html = self._generate_html(chapter_title, chapter_text)
            chapter.content = html
            chapter.add_item(self.css)
            
            self.book.add_item(chapter)
            epub_chapters.append(chapter)
        
        # 设置目录和 spine
        self.book.toc = epub_chapters
        self.book.spine = ['nav'] + epub_chapters
        
        # 添加导航
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())
        
        # 输出
        output_path = self.output_dir / f"{self.title}_zh.epub"
        epub.write_epub(output_path, self.book, {})
        
        logger.info(f"✅ EPUB 构建完成：{output_path}")
        return str(output_path)
    
    def _generate_html(self, title: str, content: str) -> str:
        """生成 HTML"""
        if not content.strip():
            content = "（无内容）"
        
        # 转义
        content = (content
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
        )
        
        # 分段
        paragraphs = content.split('\n\n')
        p_html = '\n'.join([f'<p>{p.replace(chr(10), "<br/>")}</p>' for p in paragraphs if p.strip()])
        
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh">
<head>
  <title>{title}</title>
  <link rel="stylesheet" type="text/css" href="style/main.css"/>
</head>
<body>
  <h1 class="chapter-title">{title}</h1>
  <div class="content">
    {p_html}
  </div>
</body>
</html>'''
