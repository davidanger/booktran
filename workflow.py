"""
booktran 工作流编排器 - v0.1
多模态文档翻译工具 - 将英文 PDF/EPUB 等电子书翻译为中文 EPUB
"""

import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable

from modules.parser import parse_document
from modules.chunker import Chunker, ChunkMerger
from modules.translator import Translator
from modules.summary import SummaryManager
from modules.state_manager import StateManager
from modules.epub_manual import build_epub_manual

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('booktran')


class TranslationWorkflow:
    """翻译工作流 v0.1"""
    
    def __init__(self, config_path: str, workspace_dir: str,
                 start_chapter: int = None, end_chapter: int = None):
        """
        初始化工作流
        
        Args:
            config_path: 配置文件路径
            workspace_dir: 工作目录
            start_chapter: 起始章节（可选）
            end_chapter: 结束章节（可选）
        """
        logger.info(f"🚀 初始化工作流 v0.1")
        self.config_path = config_path
        self.workspace_dir = Path(workspace_dir)
        self.task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = self.workspace_dir / "output" / self.task_id
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.start_chapter = start_chapter
        self.end_chapter = end_chapter
        
        logger.info(f"   输出目录：{self.output_dir}")
        logger.info(f"   任务 ID: {self.task_id}")
        
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        workflow_cfg = config.get('workflow', {})
        chunk_size = workflow_cfg.get('chunk_size', 2000)
        chunk_overlap = workflow_cfg.get('chunk_overlap', 0)
        
        self.chunker = Chunker(max_chars=chunk_size, overlap=chunk_overlap)
        self.translator = Translator(config_path)
        self.summary_mgr = SummaryManager(str(self.output_dir))
        self.state_mgr = StateManager(str(self.output_dir), self.task_id)
        
        logger.info("✅ 工作流初始化完成")
    
    async def run(
        self, 
        file_path: str, 
        progress_callback: Optional[Callable] = None
    ) -> str:
        """执行完整翻译工作流
        
        Args:
            file_path: 输入文件路径
            progress_callback: 进度回调函数
        
        Returns:
            输出文件路径
        """
        start_time = asyncio.get_event_loop().time()
        self.progress_callback = progress_callback or (lambda msg: logger.info(msg))
        
        logger.info("=" * 60)
        logger.info(f"📚 开始翻译任务")
        logger.info(f"   文件：{file_path}")
        logger.info(f"   时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        try:
            # 1. 解析文档
            self.progress_callback("📄 [1/6] 正在解析文档...")
            doc = await parse_document(file_path, str(self.output_dir))
            logger.info(f"✅ 解析完成")
            logger.info(f"   书名：{doc.title}")
            logger.info(f"   作者：{doc.metadata.get('author', 'Unknown')}")
            logger.info(f"   章节数：{len(doc.chapters)}")
            logger.info(f"   图片数：{len(doc.images)}")
            logger.info(f"   总字符：{doc.metadata.get('total_chars', 0):,}")
            
            # 2. 智能切片
            self.progress_callback("🔪 [2/6] 正在切片...")
            chapters_data = [
                {'id': ch.id, 'title': ch.title, 'text': ch.text}
                for ch in doc.chapters
            ]
            chunks = self.chunker.split(chapters_data)
            
            # 按章节范围过滤
            if self.start_chapter or self.end_chapter:
                filtered = []
                for c in chunks:
                    if self.start_chapter and c.chapter_id < self.start_chapter:
                        continue
                    if self.end_chapter and c.chapter_id > self.end_chapter:
                        continue
                    filtered.append(c)
                chunks = filtered
            
            logger.info(f"✅ 切片完成：{len(chunks)}片")
            
            # 3. 检查断点
            resume_chunk = await self.state_mgr.resume()
            start_chunk = resume_chunk if resume_chunk is not None else 0
            if resume_chunk is not None:
                logger.info(f"🔄 从第{start_chunk}片继续")
            
            # 4. 逐片翻译
            self.progress_callback("🔄 [3/6] 开始翻译...")
            translated_chunks = []
            chapter_titles_translated = {}
            
            for i in range(start_chunk, len(chunks)):
                chunk = chunks[i]
                
                # 翻译章节标题
                if chunk.has_chapter_title and chunk.chapter_id not in chapter_titles_translated:
                    title_prompt = f"请将以下章节标题翻译成中文：\n{chunk.chapter_title}\n\n直接输出翻译结果："
                    try:
                        title_translated = await self.translator._call_llm_api(title_prompt)
                        chapter_titles_translated[chunk.chapter_id] = title_translated.strip()
                    except Exception as e:
                        logger.warning(f"标题翻译失败：{e}")
                        chapter_titles_translated[chunk.chapter_id] = chunk.chapter_title
                
                # 翻译内容
                summary = await self.summary_mgr.load()
                prev_ending = translated_chunks[-1].text[-200:] if translated_chunks else ""
                
                translated = await self.translator.translate_chunk(
                    chunk=chunk,
                    summary_content=summary,
                    prev_translation_ending=prev_ending
                )
                
                if chunk.chapter_id in chapter_titles_translated:
                    translated.chapter_title_translated = chapter_titles_translated[chunk.chapter_id]
                
                translated_chunks.append(translated)
                await self.summary_mgr.update(i, chunk.text, translated.text)
                await self.state_mgr.save(i + 1, len(chunks), "running")
                
                # 保存切片
                chunk_file = self.output_dir / "chunks" / f"chunk_{i+1:03d}.md"
                chunk_file.parent.mkdir(parents=True, exist_ok=True)
                chunk_file.write_text(translated.text, encoding='utf-8')
                
                progress = ((i + 1) / len(chunks)) * 100
                self.progress_callback(f"🔄 [{i+1}/{len(chunks)}] ({progress:.1f}%)")
            
            logger.info(f"✅ 翻译完成")
            
            # 5. 合并章节
            self.progress_callback("📝 [5/6] 正在合并章节...")
            merger = ChunkMerger()
            chapter_texts = merger.merge(translated_chunks)
            logger.info(f"✅ 合并完成：{len(chapter_texts)}章")
            
            # 6. 构建 EPUB
            self.progress_callback("📚 [6/6] 正在构建 EPUB...")
            epub_chapters = []
            for ch in doc.chapters:
                epub_chapters.append({
                    'id': ch.id,
                    'title': chapter_titles_translated.get(ch.id, ch.title),
                    'content': chapter_texts.get(ch.id, ch.text),
                    'images': ch.images if hasattr(ch, 'images') else []
                })
            
            metadata = {
                'author': doc.metadata.get('author', 'Unknown'),
                'publisher': doc.metadata.get('publisher', ''),
                'isbn': doc.metadata.get('isbn', ''),
                'language': 'zh'
            }
            
            output_path = self.output_dir / f"{doc.title}_zh.epub"
            build_epub_manual(str(output_path), doc.title, epub_chapters, doc.images, metadata)
            epub_path = str(output_path)
            
            await self.state_mgr.complete()
            
            logger.info("=" * 60)
            logger.info(f"✅ 翻译任务完成！")
            logger.info(f"   输出：{epub_path}")
            logger.info("=" * 60)
            
            self.progress_callback(f"✅ 翻译完成！输出：{epub_path}")
            
            return epub_path
            
        except Exception as e:
            logger.error(f"❌ 任务失败：{type(e).__name__}: {e}", exc_info=True)
            await self.state_mgr.save(0, 0, "error")
            raise
