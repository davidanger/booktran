"""
翻译模块 - 调用外部 LLM API 进行翻译

修复的问题:
- API 空响应 (Qwen 模型需要 enable_thinking=false)
- 翻译重复/循环 (增强防重复提示词)
- 术语不一致 (内联格式 中文 (English))
- 标题风格混乱 (增加风格参考)
"""

import httpx
import yaml
import logging
import asyncio
from pathlib import Path
from typing import Optional
from .chunker import Chunk

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('booktran.translator')


class Translator:
    """翻译器"""
    
    def __init__(self, config_path: str):
        logger.info(f"🔧 初始化翻译器，配置文件：{config_path}")
        self.config_path = config_path
        self.config = self._load_config()
        self.base_url = self.config.get('base_url', '')
        self.api_url = f"{self.base_url}/v1/chat/completions"
        self.api_key = self.config.get('api_key', '')
        self.model = self.config.get('model', 'gpt-4')
        self.max_tokens = self.config.get('max_tokens', 4096)
        self.temperature = self.config.get('temperature', 0.7)
        self.top_p = self.config.get('top_p', 0.8)
        self.top_k = self.config.get('top_k', 20)
        self.min_p = self.config.get('min_p', 0.0)
        # v2.3 修复：Qwen 模型需要 enable_thinking=false
        self.chat_template_kwargs = self.config.get('chat_template_kwargs', {})
        logger.info(f"   Base URL: {self.base_url}")
        logger.info(f"   API URL: {self.api_url}")
        logger.info(f"   Model: {self.model}")
        logger.info(f"   Temperature: {self.temperature}, Top-P: {self.top_p}, Top-K: {self.top_k}, Min-P: {self.min_p}")
        logger.info(f"   Chat Template Kwargs: {self.chat_template_kwargs}")
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config.get('translation', {})
    
    async def translate_chunk(
        self,
        chunk: Chunk,
        summary_content: str = "",
        prev_translation_ending: str = ""
    ) -> Chunk:
        """
        翻译单个切片
        
        Args:
            chunk: 切片对象
            summary_content: 背景摘要
            prev_translation_ending: 上一片译文末尾（用于上下文衔接）
        
        Returns:
            翻译后的切片对象
        """
        logger.debug(f"   翻译第{chunk.id}片 (章节{chunk.chapter_id}, 索引{chunk.chunk_index})")
        
        # 构建 Prompt
        prompt = self._build_prompt(
            chunk_text=chunk.text,
            summary=summary_content,
            prev_translation_ending=prev_translation_ending
        )
        
        # 调用 API
        translated_text = await self._call_llm_api(prompt)
        
        # 后处理：确保内联术语格式正确（可选）
        # translated_text = self._postprocess_inline_terms(translated_text)
        
        # 创建翻译后的切片
        translated_chunk = Chunk(
            id=chunk.id,
            text=translated_text,
            chapter_id=chunk.chapter_id,
            chapter_title=chunk.chapter_title,
            chapter_title_translated=chunk.chapter_title_translated,
            chunk_index=chunk.chunk_index,
            total_chunks=chunk.total_chunks,
            start_pos=chunk.start_pos,
            end_pos=chunk.end_pos,
            is_first=chunk.is_first,
            is_last=chunk.is_last,
            has_chapter_title=chunk.has_chapter_title
        )
        
        logger.debug(f"   翻译完成：{len(chunk.text)}字符 → {len(translated_text)}字符")
        return translated_chunk
    
    def _build_prompt(
        self,
        chunk_text: str,
        summary: str,
        prev_translation_ending: str
    ) -> str:
        """构建翻译 Prompt - 双层摘要 + 内联术语 + 标题风格版"""
        return f"""# 上下文参考（仅供参考，不要翻译）
{summary if summary else "无"}

# 上一片译文末尾（仅供参考，用于上下文衔接，不要重复）
{prev_translation_ending if prev_translation_ending else "无"}

# 当前片原文（请只翻译这部分内容）
{chunk_text}

# 翻译要求

## 核心要求
1. **只翻译"当前片原文"部分**，不要翻译上下文参考和上一片译文
2. **第一句参考上一片译文末尾**，确保衔接自然，但**绝对不要重复**
3. **如果原文开头与上下文重复，直接跳过，从新内容开始翻译**

## 章节标题翻译（重要）
如果当前片包含章节标题，请参考"翻译风格指南"中的格式：
- 保持统一的标题格式（如"第 X 章：标题"）
- 参考已翻译的标题示例
- 确保目录和正文标题一致

## 术语处理（重要）
人名、地名、书名、作品名、特殊名词采用**中英文对照**格式：
- 人名：`约翰 (John)`
- 地名：`剑桥大学 (Cambridge University)`
- 书名/作品名：`《婚姻史》(A History of Marriage)`
- 特殊名词：`一夫一妻制 (monogamy)`

## 文风要求
- 参考上下文摘要中的翻译风格（正式/口语化、句式偏好等）
- 保持情节/论点连贯，不要前后矛盾
- 准确、流畅、符合中文表达习惯

## 格式要求
- 从左到右，从上到下
- 保留原文段落结构
- 保留 Markdown 格式（标题、加粗、列表等）
- 对话使用中文引号""

## 输出要求
- 直接输出翻译结果
- **不要输出思考过程、解释或额外说明**

# 请翻译以上"当前片原文"为中文（记住：不要重复上一片的内容）："""
    
    async def _call_llm_api(self, prompt: str) -> str:
        """调用 LLM API（带重试机制）"""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model,
            'messages': [
                {
                    'role': 'system',
                    'content': '你是一位专业的图书翻译家。请直接输出翻译结果，不要输出任何思考过程、解释、推理内容或额外说明。只输出最终翻译结果。'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'top_k': self.top_k,
            'min_p': self.min_p,
            'chat_template_kwargs': self.chat_template_kwargs
        }
        
        # 重试机制：最多 3 次，指数退避
        max_retries = 3
        base_delay = 5.0  # 秒
        
        for attempt in range(max_retries):
            try:
                # 增加超时时间：连接 10s，读取 300s（5 分钟）
                async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=10.0)) as client:
                    response = await client.post(
                        self.api_url,
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    result = response.json()
                    
                    if 'choices' in result and len(result['choices']) > 0:
                        message = result['choices'][0]['message']
                        # Qwen 模型可能将内容放在 reasoning_content 字段
                        translated_text = message.get('content', '')
                        reasoning_content = message.get('reasoning_content', '')
                        
                        # 如果 content 为空，使用 reasoning_content
                        if not translated_text and reasoning_content:
                            logger.warning(f"   ⚠️ content 为空，使用 reasoning_content")
                            translated_text = reasoning_content
                        
                        logger.debug(f"   API 调用成功 (尝试 {attempt + 1}/{max_retries})")
                        return translated_text.strip()
                    else:
                        logger.error(f"API 返回格式异常：{result}")
                        raise ValueError("API 返回格式异常")
            
            except httpx.ReadTimeout as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # 指数退避：5s, 10s, 20s
                    logger.warning(f"API 读取超时 (尝试 {attempt + 1}/{max_retries})，{delay}秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"API 读取超时，已重试 {max_retries} 次")
                    raise
            except httpx.HTTPError as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"HTTP 错误：{e} (尝试 {attempt + 1}/{max_retries})，{delay}秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"HTTP 错误，已重试 {max_retries} 次：{e}")
                    raise
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)
                    logger.warning(f"API 调用失败：{e} (尝试 {attempt + 1}/{max_retries})，{delay}秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"API 调用失败，已重试 {max_retries} 次：{e}")
                    raise
        
        raise Exception("API 调用失败，已达最大重试次数")


class TranslationError(Exception):
    """翻译错误"""
    pass
