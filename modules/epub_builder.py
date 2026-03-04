"""
EPUB 构建模块 - 保留完整章节结构和图片
"""

from ebooklib import epub
from pathlib import Path
from typing import List, Dict, Optional
import re
import json
import logging

logger = logging.getLogger('booktran.epub_builder')


class EPUBBuilder:
    """EPUB 构建器"""
    
    def __init__(self, output_dir: str, title: str, doc_chapters: List = None, doc_images: List = None):
        """
        Args:
            output_dir: 输出目录
            title: 书名
            doc_chapters: 原文档章节列表（用于保留结构）
            doc_images: 原文档图片列表
        """
        self.output_dir = Path(output_dir)
        self.title = title
        self.book = epub.EpubBook()
        self.doc_chapters = doc_chapters or []
        self.doc_images = doc_images or []
        self.css = self._load_css()
    
    def _load_css(self) -> str:
        """加载 CSS 样式"""
        css_file = self.output_dir / 'styles' / 'main.css'
        if css_file.exists():
            return css_file.read_text(encoding='utf-8')
        
        # 默认样式
        return '''
@page {
    margin: 10px;
}
body {
    font-family: "SimSun", "Songti SC", "Noto Serif SC", serif;
    line-height: 1.8;
    margin: 1em;
    text-align: justify;
}
h1, h2, h3 {
    text-align: center;
    margin: 1.5em 0;
    page-break-after: avoid;
}
p {
    text-indent: 2em;
    margin: 0.5em 0;
    line-height: 2;
}
img {
    max-width: 100%;
    height: auto;
    display: block;
    margin: 1em auto;
}
.chapter-title {
    font-size: 1.5em;
    font-weight: bold;
    text-align: center;
    margin: 2em 0 1em;
    page-break-before: always;
}
'''
    
    async def build(
        self,
        translated_chunks: List,
        summary: str
    ) -> str:
        """
        构建 EPUB
        
        Args:
            translated_chunks: 翻译后的切片列表（Chunk 对象）
            summary: 翻译摘要
        """
        from modules.chunker import ChunkMerger
        
        # 设置元数据
        self.book.set_identifier(f"translated-{self.title}-{Path(self.output_dir).name}")
        self.book.set_title(f"{self.title} (中文翻译)")
        self.book.set_language("zh")
        self.book.add_author("booktran translator")
        
        # 添加 CSS
        css_item = epub.EpubItem(
            uid="style",
            file_name="style/main.css",
            media_type="text/css",
            content=self.css
        )
        self.book.add_item(css_item)
        
        # 合并翻译结果（按章节）
        merger = ChunkMerger()
        chapter_texts = merger.merge(translated_chunks)
        
        logger.info(f"合并翻译结果：{len(chapter_texts)}章")
        for ch_id, text in chapter_texts.items():
            logger.info(f"  第{ch_id}章：{len(text)}字符")
        
        # 添加图片
        self._add_images()
        
        # 查找封面图片（第一张图片作为封面）
        cover_image = None
        if self.doc_images:
            cover_image = self.doc_images[0]
            logger.info(f"使用封面图片：{cover_image.get('href', 'unknown')}")
        
        # 按章节添加内容
        epub_chapters = []
        
        for chapter_id, chapter_text in chapter_texts.items():
            # 查找原章节信息
            chapter_title = f"第{chapter_id + 1}章"
            chapter_images = []
            original_content = None
            
            for doc_ch in self.doc_chapters:
                # 兼容字典和 Chapter 对象
                if hasattr(doc_ch, 'id'):
                    ch_id = doc_ch.id
                    ch_title = doc_ch.title
                    ch_images = doc_ch.images
                    ch_content = doc_ch.content
                else:
                    ch_id = doc_ch.get('id', 0)
                    ch_title = doc_ch.get('title', f"第{ch_id + 1}章")
                    ch_images = doc_ch.get('images', [])
                    ch_content = doc_ch.get('content', None)
                
                if ch_id == chapter_id:
                    chapter_title = ch_title
                    chapter_images = ch_images
                    original_content = ch_content
                    break
            
            # 特殊处理封面章节
            if chapter_title == '封面' or chapter_title.lower() == 'cover':
                # 创建封面章节
                epub_chapter = self._create_cover_chapter(chapter_id, cover_image)
            else:
                # 创建普通章节
                epub_chapter = self._create_chapter(
                    chapter_id,
                    chapter_title,
                    chapter_text,
                    chapter_images,
                    original_content
                )
            
            self.book.add_item(epub_chapter)
            epub_chapters.append(epub_chapter)
        
        # 生成目录（按章节）
        self.book.toc = epub_chapters
        
        # 设置 spine
        self.book.spine = ['nav'] + epub_chapters
        
        # 添加导航文件
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())
        
        # 设置封面元数据（EPUB2 和 EPUB3）
        if cover_image:
            self._set_cover_metadata(cover_image)
        
        # 输出 EPUB
        output_path = self.output_dir / f"{self.title}_zh.epub"
        epub.write_epub(output_path, self.book, {})
        
        return str(output_path)
    
    def _add_images(self):
        """添加图片到 EPUB"""
        images_dir = self.output_dir / 'images'
        self.image_items = {}  # 记录已添加的图片
        
        if not images_dir.exists():
            return
        
        for img_info in self.doc_images:
            try:
                img_path = Path(img_info['path'])
                if not img_path.exists():
                    continue
                
                img_data = img_path.read_bytes()
                media_type = img_info.get('media_type', 'image/jpeg')
                
                # 确定文件扩展名
                ext_map = {
                    'image/jpeg': 'jpg',
                    'image/png': 'png',
                    'image/gif': 'gif',
                    'image/webp': 'webp',
                    'image/svg+xml': 'svg',
                }
                ext = ext_map.get(media_type, 'jpg')
                
                # 创建 EPUB 图片项
                img_name = f"images/{img_path.name}"
                img_uid = f"img_{img_path.stem}"
                img_item = epub.EpubItem(
                    uid=img_uid,
                    file_name=img_name,
                    media_type=media_type,
                    content=img_data
                )
                self.book.add_item(img_item)
                self.image_items[img_path.name] = img_uid
            except Exception as e:
                print(f"添加图片失败 {img_info.get('path', 'unknown')}: {e}")
    
    def _create_cover_chapter(self, chapter_id: int, cover_image: Dict = None) -> epub.EpubHtml:
        """
        创建封面章节
        
        Args:
            chapter_id: 章节 ID
            cover_image: 封面图片信息
        """
        chapter = epub.EpubHtml(
            title='封面',
            file_name='cover.xhtml',
            lang='zh',
            uid='cover'
        )
        
        html_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh">
<head>
    <title>封面</title>
    <link rel="stylesheet" type="text/css" href="style/main.css"/>
    <style>
        body { margin: 0; padding: 0; text-align: center; }
        .cover-image { width: 100%; height: 100%; object-fit: contain; }
    </style>
</head>
<body>
'''
        
        if cover_image:
            img_name = Path(cover_image.get('path', '')).name
            if img_name:
                html_content += f'    <img src="images/{img_name}" alt="封面" class="cover-image"/>\n'
        else:
            html_content += '    <p>封面</p>\n'
        
        html_content += '''</body>
</html>'''
        
        chapter.content = html_content
        chapter.add_item(epub.EpubItem(
            uid="style",
            file_name="style/main.css",
            media_type="text/css",
            content=self.css
        ))
        
        return chapter
    
    def _set_cover_metadata(self, cover_image: Dict):
        """
        设置封面元数据（EPUB2 和 EPUB3）
        
        Args:
            cover_image: 封面图片信息
        """
        img_name = Path(cover_image.get('path', '')).name
        if not img_name or img_name not in self.image_items:
            logger.warning(f"封面图片未找到：{img_name}")
            return
        
        img_uid = self.image_items[img_name]
        
        # EPUB3 封面元数据
        self.book.add_metadata('DC', 'cover', img_uid)
        
        # EPUB2 封面元数据（guide 和 metadata）
        # 创建 cover 页面
        cover_meta = epub.EpubHtml(
            title='Cover',
            file_name='cover_meta.xhtml',
            lang='zh'
        )
        cover_meta.content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head><title>Cover</title></head>
<body epub:type="cover">
    <img src="images/{img_name}" alt="Cover" style="width:100%;height:100%"/>
</body>
</html>'''
        self.book.add_item(cover_meta)
        
        # 添加到 spine（作为第一个元素，但标记为不显示）
        # self.book.spine.insert(0, (cover_meta, 'no'))
        
        logger.info(f"✅ 封面元数据已设置：{img_name} (UID: {img_uid})")
    
    def _create_chapter(
        self,
        chapter_id: int,
        title: str,
        content: str,
        images: List[Dict] = None,
        original_content: str = None  # 原文档的 XHTML 内容
    ) -> epub.EpubHtml:
        """
        创建章节
        
        Args:
            chapter_id: 章节 ID
            title: 章节标题
            content: 章节内容（纯文本）
            images: 图片列表
            original_content: 原文档的 XHTML 内容（用于保留图片位置）
        """
        chapter = epub.EpubHtml(
            title=title,
            file_name=f"chapter_{chapter_id + 1}.xhtml",
            lang="zh",
            uid=f"chapter_{chapter_id + 1}"
        )
        
        html_content = self._content_to_html(title, content, images, original_content)
        chapter.content = html_content
        chapter.add_item(epub.EpubItem(
            uid="style",
            file_name="style/main.css",
            media_type="text/css",
            content=self.css
        ))
        
        return chapter
    
    def _content_to_html(
        self,
        title: str,
        content: str,
        images: List[Dict] = None,
        original_content: str = None  # 原文档的 XHTML 内容
    ) -> str:
        """
        内容转 HTML
        
        Args:
            title: 章节标题
            content: 章节内容（翻译后的文本）
            images: 图片列表
            original_content: 原文档的 XHTML 内容（用于保留图片位置）
        """
        html_parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<!DOCTYPE html>',
            '<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh">',
            '<head>',
            f'  <title>{self._escape_xml(title)}</title>',
            '  <link rel="stylesheet" type="text/css" href="style/main.css"/>',
            '</head>',
            '<body>',
            f'  <h1 class="chapter-title">{self._escape_xml(title)}</h1>',
        ]
        
        # 如果有原文档的 XHTML 内容，尝试保留图片位置
        if original_content and images:
            # 从原文中提取图片标签并插入到翻译文本中
            html_parts.append(self._merge_translation_with_images(content, original_content, images))
        else:
            # 简单模式：在章节开头添加所有图片
            if images:
                html_parts.append('  <div class="images-section">')
                for img_info in images:
                    img_name = Path(img_info.get('path', img_info.get('href', ''))).name
                    if img_name:
                        html_parts.append(f'    <img src="images/{img_name}" alt="图片"/>')
                html_parts.append('  </div>')
            
            # 添加正文
            html_parts.append('  <div class="content">')
            if content.strip():
                paragraphs = content.split('\n\n')
                for p in paragraphs:
                    if p.strip():
                        p_escaped = self._escape_xml(p)
                        p_escaped = p_escaped.replace('\n', '<br/>')
                        html_parts.append(f'    <p>{p_escaped}</p>')
            else:
                html_parts.append('    <p>（无内容）</p>')
            html_parts.append('  </div>')
        
        html_parts.append('</body>')
        html_parts.append('</html>')
        
        return '\n'.join(html_parts)
    
    def _merge_translation_with_images(
        self,
        translation: str,
        original_xhtml: str,
        images: List[Dict]
    ) -> str:
        """
        将翻译文本与原文档的图片位置合并
        
        策略：按段落对应，在对应位置插入图片
        """
        # 从原文中提取图片标签及其位置
        img_pattern = r'<img[^>]+src=["\']([^"\']+)["\'][^>]*>'
        img_matches = list(re.finditer(img_pattern, original_xhtml))
        
        if not img_matches:
            # 没有图片，直接返回翻译文本
            return self._text_to_html_content(translation)
        
        # 提取原文的段落结构
        original_text = re.sub(r'<[^>]+>', '', original_xhtml)
        original_paragraphs = [p.strip() for p in original_text.split('\n\n') if p.strip()]
        
        # 翻译的段落
        translated_paragraphs = [p.strip() for p in translation.split('\n\n') if p.strip()]
        
        # 创建图片位置映射（基于段落索引）
        img_by_paragraph = {}
        for i, img_match in enumerate(img_matches):
            # 找到图片在原文中的位置（字符偏移）
            img_pos = img_match.start()
            
            # 计算这个位置属于哪个段落
            char_count = 0
            para_idx = 0
            for j, para in enumerate(original_paragraphs):
                if char_count + len(para) >= img_pos:
                    para_idx = j
                    break
                char_count += len(para)
            
            if para_idx not in img_by_paragraph:
                img_by_paragraph[para_idx] = []
            img_by_paragraph[para_idx].append(img_match.group(0))
        
        # 构建 HTML 内容
        html_content_parts = ['  <div class="content">']
        
        for i, para in enumerate(translated_paragraphs):
            # 先添加该段落的图片（如果有）
            if i in img_by_paragraph:
                for img_tag in img_by_paragraph[i]:
                    # 转换图片标签为 EPUB 格式
                    src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag)
                    if src_match:
                        img_src = src_match.group(1)
                        img_name = Path(img_src).name
                        html_content_parts.append(f'    <img src="images/{img_name}" alt="图片"/>')
            
            # 添加段落文本
            para_escaped = self._escape_xml(para)
            para_escaped = para_escaped.replace('\n', '<br/>')
            html_content_parts.append(f'    <p>{para_escaped}</p>')
        
        # 处理剩余的图片和段落
        remaining_imgs = sum(len(v) for k, v in img_by_paragraph.items() if k >= len(translated_paragraphs))
        if remaining_imgs > 0:
            html_content_parts.append('    <div class="remaining-images">')
            for i in range(len(translated_paragraphs), max(img_by_paragraph.keys()) + 1 if img_by_paragraph else 0):
                if i in img_by_paragraph:
                    for img_tag in img_by_paragraph[i]:
                        src_match = re.search(r'src=["\']([^"\']+)["\']', img_tag)
                        if src_match:
                            img_src = src_match.group(1)
                            img_name = Path(img_src).name
                            html_content_parts.append(f'    <img src="images/{img_name}" alt="图片"/>')
            html_content_parts.append('    </div>')
        
        html_content_parts.append('  </div>')
        
        return '\n'.join(html_content_parts)
    
    def _text_to_html_content(self, text: str) -> str:
        """简单文本转 HTML 内容"""
        html_parts = ['  <div class="content">']
        if text and text.strip():
            paragraphs = text.split('\n\n')
            for p in paragraphs:
                if p.strip():
                    p_escaped = self._escape_xml(p)
                    p_escaped = p_escaped.replace('\n', '<br/>')
                    html_parts.append(f'    <p>{p_escaped}</p>')
        else:
            html_parts.append('    <p>（图片页）</p>')
        html_parts.append('  </div>')
        return '\n'.join(html_parts)
    
    def _escape_xml(self, text: str) -> str:
        """XML 转义"""
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;')
        )
