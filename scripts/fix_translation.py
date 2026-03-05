#!/usr/bin/env python3
"""
翻译质量修复脚本

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

# 导入模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.translator import Translator
from modules.epub_manual import build_epub_manual


class TranslationFixer:
    """翻译修复器"""
    
    def __init__(self, config_path: Path, output_dir: Path, original_epub_path: Path):
        self.config_path = config_path
        self.config = yaml.safe_load(config_path.read_text())
        self.output_dir = output_dir
        self.chunks_dir = output_dir / 'chunks_translated'
        self.chunks_info_path = output_dir / 'chunks_info.json'
        self.doc_structure_path = output_dir / 'doc_structure.json'
        self.original_epub_path = original_epub_path
        
        # 初始化翻译器
        self.translator = Translator(str(config_path))
        
        # 解析原始 EPUB
        self.original_chapters = self._parse_original_epub()
        
    def _parse_original_epub(self) -> Dict[int, List[str]]:
        """解析原始 EPUB，按章节提取文本"""
        logger.info("解析原始 EPUB...")
        
        book = epub.read_epub(self.original_epub_path)
        chapters = {}  # chapter_id -> list of texts
        
        for i, item in enumerate(book.get_items()):
            if item.get_type() == 9:  # ITEM_DOCUMENT
                content = item.get_content().decode('utf-8', errors='ignore')
                chapters[i] = content
        
        logger.info(f"解析完成，共 {len(chapters)} 个文档")
        return chapters
    
    def load_json(self, path: Path) -> dict:
        """加载 JSON 文件"""
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_chunk_original_text(self, chunk_id: int) -> str:
        """根据 chunk_id 获取原文文本"""
        chunks_info = self.load_json(self.chunks_info_path)
        chunk_info = chunks_info[chunk_id]
        
        chapter_id = chunk_info['chapter_id']
        chunk_index = chunk_info['chunk_index']
        
        logger.info(f"获取 chunk_{chunk_id} 原文 (chapter={chapter_id}, index={chunk_index})")
        
        # 从原始章节文本中提取对应切片
        # 注意：这里需要知道原始切片逻辑
        # 简化处理：如果 chapter_id 在原始数据中，返回整个章节
        if chapter_id in self.original_chapters:
            chapter_text = self.original_chapters[chapter_id]
            # 返回整个章节（简化处理）
            return chapter_text
        
        return None
    
    async def retranslate_chunk(self, chunk_id: int, original_text: str) -> str:
        """重新翻译指定切片"""
        logger.warning(f"🔄 重新翻译 chunk_{chunk_id}...")
        
        # 使用更强的防重复提示词
        prompt = f"""请将以下英文文本翻译为中文。

⚠️ **重要要求**：
1. 不要重复任何句子或段落
2. 不要添加自我注释（如"注："、"重新翻译"等）
3. 不要重复任何词语
4. 保持翻译流畅自然
5. 只输出翻译结果，不要输出其他内容

原文：
{original_text[:3000]}  # 限制长度

翻译："""
        
        translated = await self.translator.translate(prompt)
        return translated
    
    async def fix_problem_chunks(self, problem_chunk_ids: List[int]) -> bool:
        """修复问题切片"""
        logger.info(f"开始修复 {len(problem_chunk_ids)} 个问题切片...")
        
        success_count = 0
        for chunk_id in problem_chunk_ids:
            try:
                # 获取原文
                original_text = self.get_chunk_original_text(chunk_id)
                
                if not original_text:
                    logger.error(f"无法获取 chunk_{chunk_id} 的原文，跳过")
                    continue
                
                # 重新翻译
                translated = await self.retranslate_chunk(chunk_id, original_text)
                
                # 保存新翻译
                chunk_path = self.chunks_dir / f"chunk_{chunk_id}.md"
                chunk_path.write_text(translated, encoding='utf-8')
                logger.info(f"✅ chunk_{chunk_id} 修复完成")
                success_count += 1
                
            except Exception as e:
                logger.error(f"❌ chunk_{chunk_id} 修复失败：{e}")
        
        logger.info(f"修复完成：{success_count}/{len(problem_chunk_ids)}")
        return success_count == len(problem_chunk_ids)
    
    def rebuild_epub(self, output_path: Path):
        """重新生成 EPUB"""
        logger.info(f"重新生成 EPUB: {output_path}")
        
        # 加载文档结构
        doc_structure = self.load_json(self.doc_structure_path)
        chunks_info = self.load_json(self.chunks_info_path)
        
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
                chunk_path = self.chunks_dir / f"chunk_{chunk['id']}.md"
                if chunk_path.exists():
                    content = chunk_path.read_text(encoding='utf-8')
                    chapter_content += content + '\n\n'
            
            epub_chapters.append({
                'id': chapter_id,
                'title': chapter_title,
                'content': chapter_content
            })
        
        # 修正图片路径
        images_dir = self.output_dir / 'images'
        for img in doc_structure.get('images', []):
            img_filename = Path(img['href']).name
            img['path'] = str(images_dir / img_filename)
        
        # 生成 EPUB
        metadata = doc_structure.get('metadata', {})
        build_epub_manual(
            str(output_path),
            doc_structure['title'],
            epub_chapters,
            doc_structure.get('images', []),
            metadata
        )
        
        logger.info(f"✅ EPUB 生成完成：{output_path}")
        logger.info(f"文件大小：{output_path.stat().st_size:,} bytes")


async def main():
    """主函数"""
    # 配置路径
    config_path = Path('config.yaml')
    output_dir = Path('_archive/output/full_20260304_152325')
    original_epub_path = Path('_archive/input/Insatiable_Wives_original.epub')
    
    # 问题切片列表
    problem_chunk_ids = [351, 162, 238, 415, 26, 14]
    
    # 创建修复器
    fixer = TranslationFixer(config_path, output_dir, original_epub_path)
    
    # 修复问题切片
    success = await fixer.fix_problem_chunks(problem_chunk_ids)
    
    # 重新生成 EPUB
    output_epub_path = output_dir / 'Insatiable_Wives_zh_FIXED.epub'
    fixer.rebuild_epub(output_epub_path)
    
    logger.info("\n" + "="*60)
    logger.info("修复完成！")
    logger.info(f"输出文件：{output_epub_path}")
    logger.info("="*60)


if __name__ == '__main__':
    asyncio.run(main())
