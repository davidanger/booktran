#!/usr/bin/env python3
"""
翻译质量修复脚本（简化版）

重新翻译问题切片，然后重新生成 EPUB
"""

import asyncio
import json
import yaml
import logging
from pathlib import Path
from typing import List, Dict
from ebooklib import epub

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def translate_text(text: str, config: dict) -> str:
    """直接调用 LLM API 翻译"""
    import httpx
    
    api_url = f"{config['base_url']}/v1/chat/completions"
    api_key = config['api_key']
    model = config['model']
    
    prompt = f"""请将以下英文文本翻译为中文。

⚠️ **重要要求**：
1. 不要重复任何句子或段落
2. 不要添加自我注释（如"注："、"重新翻译"等）
3. 不要重复任何词语
4. 保持翻译流畅自然
5. 只输出翻译结果，不要输出其他内容

原文：
{text[:3000]}

翻译："""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": config.get('temperature', 0.7),
        "top_p": config.get('top_p', 0.8),
        "max_tokens": config.get('max_tokens', 4096)
    }
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        return result['choices'][0]['message']['content']


def extract_original_chunk(original_epub_path: Path, chapter_id: int, chunks_info: list, chunk_id: int) -> str:
    """从原始 EPUB 提取对应切片的原文"""
    # 解析原始 EPUB
    book = epub.read_epub(original_epub_path)
    
    # 获取所有文档内容
    docs = {}
    for i, item in enumerate(book.get_items()):
        if item.get_type() == 9:
            content = item.get_content().decode('utf-8', errors='ignore')
            docs[i] = content
    
    # 根据 chapter_id 找到对应的原始文档
    # 这里需要一个映射关系：chapter_id -> doc_index
    # 从之前的输出看：
    # chapter_id=0-5: 封面、半标题等（doc_19-24）
    # chapter_id=6: INTRODUCTION (doc_25)
    # chapter_id=7: BIRDS AND HORNS (doc_32)
    # ...
    
    # 简化：直接使用章节标题匹配
    chunk_info = chunks_info[chunk_id]
    chapter_title = chunk_info['chapter_title']
    
    # 查找匹配的文档
    for doc_idx, content in docs.items():
        if chapter_title.upper() in content[:500].upper():
            logger.info(f"找到匹配文档：doc_{doc_idx} (chapter_title={chapter_title})")
            return content
    
    # 如果找不到，返回 None
    logger.warning(f"未找到 chapter_id={chapter_id} 的原文")
    return None


async def fix_problem_chunks(config: dict, output_dir: Path, original_epub_path: Path, problem_chunk_ids: List[int]):
    """修复问题切片"""
    chunks_dir = output_dir / 'chunks_translated'
    chunks_info_path = output_dir / 'chunks_info.json'
    
    chunks_info = json.load(open(chunks_info_path, 'r'))
    
    logger.info(f"开始修复 {len(problem_chunk_ids)} 个问题切片...")
    
    for chunk_id in problem_chunk_ids:
        try:
            chunk_info = chunks_info[chunk_id]
            chapter_id = chunk_info['chapter_id']
            
            logger.info(f"\n{'='*60}")
            logger.info(f"处理 chunk_{chunk_id} (chapter={chapter_id}, title={chunk_info['chapter_title']})")
            
            # 获取原文
            original_text = extract_original_chunk(original_epub_path, chapter_id, chunks_info, chunk_id)
            
            if not original_text:
                logger.error(f"无法获取原文，跳过 chunk_{chunk_id}")
                continue
            
            # 重新翻译
            logger.info(f"🔄 重新翻译中...")
            translated = await translate_text(original_text, config)
            
            # 保存新翻译
            chunk_path = chunks_dir / f"chunk_{chunk_id}.md"
            chunk_path.write_text(translated, encoding='utf-8')
            logger.info(f"✅ chunk_{chunk_id} 修复完成 ({len(translated)} chars)")
            
        except Exception as e:
            logger.error(f"❌ chunk_{chunk_id} 修复失败：{e}")
            import traceback
            traceback.print_exc()


def rebuild_epub(output_dir: Path, output_epub_path: Path):
    """重新生成 EPUB"""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from modules.epub_manual import build_epub_manual
    
    logger.info(f"重新生成 EPUB: {output_epub_path}")
    
    # 加载文档结构
    doc_structure_path = output_dir / 'doc_structure.json'
    chunks_info_path = output_dir / 'chunks_info.json'
    
    doc_structure = json.load(open(doc_structure_path, 'r'))
    chunks_info = json.load(open(chunks_info_path, 'r'))
    
    # 准备章节数据
    epub_chapters = []
    for chapter in doc_structure['chapters']:
        chapter_id = chapter['id']
        chapter_title = chapter['title']
        
        # 收集该章节的所有切片
        chapter_chunks = [c for c in chunks_info if c['chapter_id'] == chapter_id]
        chapter_chunks.sort(key=lambda x: x['chunk_index'])
        
        chapter_content = ''
        for chunk in chapter_chunks:
            chunk_path = output_dir / 'chunks_translated' / f"chunk_{chunk['id']}.md"
            if chunk_path.exists():
                content = chunk_path.read_text(encoding='utf-8')
                chapter_content += content + '\n\n'
        
        epub_chapters.append({
            'id': chapter_id,
            'title': chapter_title,
            'content': chapter_content
        })
    
    # 修正图片路径
    images_dir = output_dir / 'images'
    for img in doc_structure.get('images', []):
        img_filename = Path(img['href']).name
        img['path'] = str(images_dir / img_filename)
    
    # 生成 EPUB
    metadata = doc_structure.get('metadata', {})
    build_epub_manual(
        str(output_epub_path),
        doc_structure['title'],
        epub_chapters,
        doc_structure.get('images', []),
        metadata
    )
    
    logger.info(f"✅ EPUB 生成完成：{output_epub_path}")
    logger.info(f"文件大小：{output_epub_path.stat().st_size:,} bytes")


async def main():
    """主函数"""
    # 配置路径
    config_path = Path('config.yaml')
    config = yaml.safe_load(config_path.read_text())['translation']
    
    output_dir = Path('_archive/output/full_20260304_152325')
    original_epub_path = Path('_archive/input/Insatiable_Wives_original.epub')
    
    # 问题切片列表
    problem_chunk_ids = [351, 162, 238, 415, 26, 14]
    
    # 修复问题切片
    await fix_problem_chunks(config, output_dir, original_epub_path, problem_chunk_ids)
    
    # 重新生成 EPUB
    output_epub_path = output_dir / 'Insatiable_Wives_zh_FIXED.epub'
    rebuild_epub(output_dir, output_epub_path)
    
    logger.info("\n" + "="*60)
    logger.info("修复完成！")
    logger.info(f"输出文件：{output_epub_path}")
    logger.info("="*60)


if __name__ == '__main__':
    asyncio.run(main())
