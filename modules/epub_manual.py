#!/usr/bin/env python3
"""手动构建 EPUB - 完整支持图片、元数据、封面、章节目录"""

import zipfile
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import logging
import re

logger = logging.getLogger('booktran.epub_manual')


def build_epub_manual(
    output_path: str,
    title: str,
    chapters: List[Dict],
    images: List[Dict] = None,
    metadata: Dict = None
) -> str:
    """
    手动构建 EPUB 文件
    
    Args:
        output_path: 输出路径
        title: 书名
        chapters: 章节列表 [{'id': 0, 'title': '第 1 章', 'content': '...', 'images': [...]}]
        images: 图片列表 [{'path': '...', 'href': '...', 'media_type': '...'}]
        metadata: 元数据 {'author': '...', 'publisher': '...', 'isbn': '...', 'language': '...'}
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"开始构建 EPUB: {output_path}")
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as epub:
        # 1. mimetype (必须不压缩且第一个)
        epub.writestr('mimetype', 'application/epub+zip', compress_type=zipfile.ZIP_STORED)
        
        # 2. META-INF/container.xml
        container = '''<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>'''
        epub.writestr('META-INF/container.xml', container)
        
        # 3. content.opf
        opf = generate_opf(title, chapters, images, metadata)
        epub.writestr('content.opf', opf)
        
        # 4. nav.xhtml (EPUB3 导航)
        nav = generate_nav(title, chapters)
        epub.writestr('nav.xhtml', nav)
        
        # 5. toc.ncx (EPUB2 导航)
        ncx = generate_ncx(title, chapters)
        epub.writestr('toc.ncx', ncx)
        
        # 6. CSS
        css = '''body { font-family: "SimSun", "Noto Serif SC", serif; line-height: 1.8; margin: 1em; text-align: justify; }
h1 { text-align: center; margin: 1.5em 0; page-break-after: avoid; font-size: 1.5em; }
p { text-indent: 2em; margin: 0.5em 0; }
img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
.chapter-title { font-size: 1.5em; font-weight: bold; text-align: center; margin: 2em 0 1em; page-break-before: always; }
.cover-page { text-align: center; margin: 0; padding: 0; }
.cover-page img { max-width: 100%; max-height: 100%; margin: 0; }
'''
        epub.writestr('style/main.css', css)
        
        # 7. 封面页（如果有封面图片）
        # 查找真正的封面图片：优先使用 frn_（front）前缀的图片
        cover_img = None
        if images:
            # 优先查找 frn_ 前缀的图片（front figure = 封面）
            for img in images:
                img_name = Path(img.get('path', '')).name.lower()
                if img_name.startswith('frn_'):
                    cover_img = img
                    break
            # 如果没有 frn_ 图片，使用第一张图片
            if not cover_img:
                cover_img = images[0]
        
        if cover_img:
            cover_img_name = Path(cover_img.get('path', '')).name
            cover_xhtml = generate_cover_xhtml(title, cover_img_name)
            epub.writestr('cover.xhtml', cover_xhtml)
            logger.info(f"  ✅ 添加封面：{cover_img_name}")
        
        # 8. 章节文件（包含图片）
        for ch in chapters:
            # 获取章节图片
            ch_images = ch.get('images', [])
            xhtml = generate_chapter_xhtml(ch['title'], ch['content'], ch_images)
            epub.writestr(f"chapter_{ch['id'] + 1}.xhtml", xhtml)
        
        # 9. 图片文件
        if images:
            for i, img in enumerate(images):
                try:
                    img_path = Path(img.get('path', ''))
                    if img_path.exists():
                        img_data = img_path.read_bytes()
                        img_name = img_path.name
                        epub.writestr(f'images/{img_name}', img_data)
                        logger.info(f"  ✅ 添加图片：{img_name}")
                    else:
                        logger.warning(f"  ⚠️ 图片不存在：{img_path}")
                except Exception as e:
                    logger.warning(f"  ❌ 图片添加失败 {img.get('path')}: {e}")
    
    logger.info(f"✅ EPUB 构建完成：{output_path} ({output_path.stat().st_size / 1024:.1f} KB)")
    return str(output_path)


def generate_opf(title: str, chapters: List[Dict], images: List[Dict] = None, metadata: Dict = None) -> str:
    """生成 content.opf - 包含完整元数据"""
    timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ')
    
    # 提取元数据
    author = metadata.get('author', 'Unknown') if metadata else 'Unknown'
    publisher = metadata.get('publisher', '') if metadata else ''
    isbn = metadata.get('isbn', '') if metadata else ''
    if not isbn:
        isbn = f'translated-{title.replace(" ", "-").replace("_", "-")}'
    language = metadata.get('language', 'zh') if metadata else 'zh'
    
    # 查找封面图片：优先使用 frn_（front）前缀的图片
    cover_image_id = ''
    cover_image_href = ''
    cover_image_idx = 0
    if images:
        # 优先查找 frn_ 前缀的图片（front figure = 封面）
        for i, img in enumerate(images):
            img_name = Path(img.get('path', '')).name.lower()
            if img_name.startswith('frn_'):
                cover_image_href = img.get('href', img.get('path', ''))
                cover_image_id = f'img{i}'
                cover_image_idx = i
                break
        # 如果没有 frn_ 图片，使用第一张图片
        if not cover_image_href and images:
            cover_image_href = images[0].get('href', images[0].get('path', ''))
            cover_image_id = 'img0'
    
    # 构建 manifest items
    manifest_items = [
        '    <item id="ncx" href="toc.ncx" media-type="application/x-dtbncx+xml"/>',
        '    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>',
        '    <item id="css" href="style/main.css" media-type="text/css"/>',
    ]
    
    # 添加封面页（如果有）
    if cover_image_id:
        manifest_items.append('    <item id="cover" href="cover.xhtml" media-type="application/xhtml+xml"/>')
    
    # 添加章节
    for ch in chapters:
        manifest_items.append(f'    <item id="chapter{ch["id"]+1}" href="chapter_{ch["id"]+1}.xhtml" media-type="application/xhtml+xml"/>')
    
    # 添加图片
    if images:
        for i, img in enumerate(images):
            img_name = Path(img.get('path', f'img{i}')).name
            media_type = img.get('media_type', 'image/jpeg')
            manifest_items.append(f'    <item id="img{i}" href="images/{img_name}" media-type="{media_type}"/>')
    
    # 添加封面图片项（EPUB3 cover-image property）
    if cover_image_id:
        img_name = Path(cover_image_href).name
        media_type = images[0].get('media_type', 'image/jpeg') if images else 'image/jpeg'
        manifest_items.append(f'    <item id="cover-image" href="images/{img_name}" media-type="{media_type}" properties="cover-image"/>')
    
    # 构建 spine（封面作为第一个元素）
    spine_items = []
    if cover_image_id:
        spine_items.append('    <itemref idref="cover" linear="no"/>')
    for i in range(len(chapters)):
        spine_items.append(f'    <itemref idref="chapter{i+1}"/>')
    
    # 构建 metadata
    metadata_xml = f'''    <dc:identifier id="uid">{isbn}</dc:identifier>
    <dc:title>{title}</dc:title>
    <dc:creator id="creator">{author}</dc:creator>
    <dc:language>{language}</dc:language>'''
    
    if publisher:
        metadata_xml += f'\n    <dc:publisher>{publisher}</dc:publisher>'
    
    metadata_xml += f'\n    <meta property="dcterms:modified">{timestamp}</meta>'
    
    # 添加封面元数据（EPUB2 和 EPUB3）
    if cover_image_id:
        metadata_xml += f'\n    <meta name="cover" content="{cover_image_id}"/>'
    
    # 构建 guide（EPUB2 封面指引）
    guide_xml = ''
    if cover_image_id:
        guide_xml = f'''
  <guide>
    <reference type="cover" title="Cover" href="cover.xhtml"/>
  </guide>'''
    
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="uid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
{metadata_xml}
  </metadata>
  <manifest>
{chr(10).join(manifest_items)}
  </manifest>
  <spine toc="ncx" page-progression-direction="ltr">
{chr(10).join(spine_items)}
  </spine>{guide_xml}
</package>'''


def generate_nav(title: str, chapters: List[Dict]) -> str:
    """生成 nav.xhtml - 目录导航"""
    nav_items = '\n'.join([
        f'      <li><a href="chapter_{ch["id"]+1}.xhtml">{escape_xml(ch["title"])}</a></li>'
        for ch in chapters
    ])
    
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
  <title>目录 - {escape_xml(title)}</title>
</head>
<body>
<nav epub:type="toc">
  <h1>目录</h1>
  <ol>
{nav_items}
  </ol>
</nav>
</body>
</html>'''


def generate_ncx(title: str, chapters: List[Dict]) -> str:
    """生成 toc.ncx - EPUB2 导航"""
    nav_points = '\n'.join([
        f'''    <navPoint id="navpoint-{i+1}" playOrder="{i+1}">
      <navLabel><text>{escape_xml(ch["title"])}</text></navLabel>
      <content src="chapter_{i+1}.xhtml"/>
    </navPoint>'''
        for i, ch in enumerate(chapters)
    ])
    
    safe_title = title.replace(" ", "-").replace("_", "-")
    
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">
<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">
  <head>
    <meta name="dtb:uid" content="translated-{safe_title}"/>
    <meta name="dtb:depth" content="1"/>
    <meta name="dtb:totalPageCount" content="0"/>
    <meta name="dtb:maxPageNumber" content="0"/>
  </head>
  <docTitle><text>{escape_xml(title)}</text></docTitle>
  <navMap>
{nav_points}
  </navMap>
</ncx>'''


def generate_cover_xhtml(title: str, image_name: str) -> str:
    """生成封面页 XHTML"""
    def escape_xml(text):
        if text:
            return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;')
            )
        return ""
    
    title_escaped = escape_xml(title)
    
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh">
<head>
  <title>封面</title>
  <link rel="stylesheet" type="text/css" href="style/main.css"/>
  <style>
    body {{ margin: 0; padding: 0; text-align: center; }}
    .cover-page {{ width: 100%; height: 100%; text-align: center; margin: 0; padding: 0; }}
    .cover-page img {{ max-width: 100%; max-height: 100%; width: auto; height: auto; margin: 0; padding: 0; }}
  </style>
</head>
<body>
  <div class="cover-page">
    <img src="images/{image_name}" alt="封面" epub:type="cover"/>
  </div>
</body>
</html>'''


def generate_chapter_xhtml(title: str, content: str, images: list = None) -> str:
    """生成章节 XHTML - 包含图片和标题"""
    # XML 转义
    def escape_xml(text):
        if text:
            return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&apos;')
            )
        return ""
    
    title_escaped = escape_xml(title)
    
    # 处理内容 - 分段和换行
    if content:
        # 按段落分割
        paragraphs = content.split('\n\n')
        p_html_list = []
        
        for p in paragraphs:
            if p.strip():
                # 处理段落内的换行
                p_text = escape_xml(p.strip())
                p_text = p_text.replace('\n', '<br/>')
                p_html_list.append(f'<p>{p_text}</p>')
        
        p_html = '\n    '.join(p_html_list)
    else:
        p_html = ''
    
    # 处理图片
    img_html = ''
    if images:
        for img in images:
            img_path = img.get('path', img.get('href', ''))
            if img_path:
                img_name = Path(img_path).name
                img_html += f'    <img src="images/{img_name}" alt="插图"/>\n'
    
    # 构建 XHTML
    body_content = f'  <h1 class="chapter-title">{title_escaped}</h1>\n'
    
    if img_html:
        body_content += f'  <div class="images">\n{img_html}  </div>\n'
    
    if p_html:
        body_content += f'  <div class="content">\n    {p_html}\n  </div>'
    elif not img_html:
        body_content += '  <p>（空章节）</p>'
    
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="zh">
<head>
  <title>{title_escaped}</title>
  <link rel="stylesheet" type="text/css" href="style/main.css"/>
</head>
<body>
{body_content}
</body>
</html>'''


def escape_xml(text: str) -> str:
    """XML 转义辅助函数"""
    if text:
        return (text
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;')
        )
    return ""
