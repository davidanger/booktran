#!/usr/bin/env python3
"""
翻译质量兜底检查脚本

在所有切片翻译完成后运行，检测并修复重复问题。
"""

import asyncio
import logging
import yaml
from pathlib import Path
from typing import List, Dict
from modules.repetition_checker import check_top_chunks, check_chunk_file
from modules.translator import Translator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QualityChecker:
    """翻译质量检查器"""
    
    def __init__(self, config_path: Path, output_dir: Path):
        self.config = yaml.safe_load(config_path.read_text())
        self.output_dir = output_dir
        self.chunks_dir = output_dir / 'chunks_translated'
        self.chunks_info_path = output_dir / 'chunks_info.json'
        self.max_iterations = 10
        self.top_n = 3  # 每次检查最大的 N 个文件
        
    def load_chunks_info(self) -> List[Dict]:
        """加载切片信息（包含原文映射）"""
        import json
        if not self.chunks_info_path.exists():
            logger.warning(f"切片信息文件不存在：{self.chunks_info_path}")
            return []
        
        with open(self.chunks_info_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def get_original_text(self, chunk_id: int, chunks_info: List[Dict]) -> str:
        """根据 chunk_id 获取原文文本"""
        # TODO: 需要从原文档中提取对应位置的原文
        # 这里需要根据实际的切片逻辑实现
        logger.info(f"获取 chunk_{chunk_id} 的原文")
        return ""
    
    async def retranslate_chunk(self, chunk_id: int, original_text: str) -> str:
        """重新翻译指定切片"""
        logger.warning(f"重新翻译 chunk_{chunk_id}...")
        
        translator = Translator(
            api_key=self.config['translation']['api_key'],
            base_url=self.config['translation']['base_url'],
            model=self.config['translation']['model']
        )
        
        # 使用更强的防重复提示词
        prompt = f"""请将以下英文文本翻译为中文。

⚠️ **重要要求**：
1. 不要重复任何句子或段落
2. 不要添加自我注释（如"注："、"重新翻译"等）
3. 不要重复任何词语
4. 保持翻译流畅自然
5. 只输出翻译结果，不要输出其他内容

原文：
{original_text}

翻译："""
        
        translated = await translator.translate(prompt)
        return translated
    
    def check_and_fix(self) -> bool:
        """检查并修复问题切片
        
        Returns:
            bool: 是否所有检查都通过
        """
        import json
        
        chunks_info = self.load_chunks_info()
        
        for iteration in range(self.max_iterations):
            logger.info(f"\n{'='*60}")
            logger.info(f"第 {iteration + 1}/{self.max_iterations} 轮检查")
            logger.info(f"{'='*60}")
            
            # 检查体积最大的 N 个切片
            results = check_top_chunks(self.output_dir, top_n=self.top_n)
            
            # 过滤出有问题的切片
            problem_chunks = [r for r in results if r.get('has_issues', False)]
            
            if not problem_chunks:
                logger.info("✅ 质量检查通过！所有切片正常。")
                return True
            
            logger.warning(f"发现 {len(problem_chunks)} 个问题切片:")
            for result in problem_chunks:
                chunk_id = result.get('chunk_id', 'unknown')
                issues = result.get('issues', [])
                logger.warning(f"  - {chunk_id}: {issues}")
            
            # 重新翻译问题切片
            for result in problem_chunks:
                chunk_id_str = result.get('chunk_id', '')
                chunk_id = int(chunk_id_str.replace('chunk_', ''))
                
                # 获取原文
                original_text = self.get_original_text(chunk_id, chunks_info)
                
                if not original_text:
                    logger.error(f"无法获取 chunk_{chunk_id} 的原文，跳过")
                    continue
                
                # 重新翻译
                translated = asyncio.run(self.retranslate_chunk(chunk_id, original_text))
                
                # 保存新翻译
                chunk_path = self.chunks_dir / f"{chunk_id_str}.md"
                chunk_path.write_text(translated, encoding='utf-8')
                logger.info(f"✅ chunk_{chunk_id} 重新翻译完成")
        
        logger.error(f"\n⚠️ 达到最大循环次数 {self.max_iterations}，仍有问题切片")
        return False
    
    def generate_report(self) -> str:
        """生成质量检查报告"""
        results = check_top_chunks(self.output_dir, top_n=10)
        
        report = []
        report.append("# 翻译质量检查报告\n")
        report.append(f"检查时间：{Path(self.output_dir).stat().st_mtime}\n")
        report.append(f"检查切片数：{len(results)}\n\n")
        
        has_issues = any(r.get('has_issues', False) for r in results)
        
        if has_issues:
            report.append("## ⚠️ 发现问题\n\n")
            for result in results:
                if result.get('has_issues'):
                    chunk_id = result.get('chunk_id')
                    issues = result.get('issues', [])
                    report.append(f"- **{chunk_id}**: {issues}\n")
        else:
            report.append("## ✅ 检查结果：全部通过\n\n")
        
        return "".join(report)


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='翻译质量兜底检查')
    parser.add_argument('--config', type=str, default='config.yaml',
                       help='配置文件路径')
    parser.add_argument('--output', type=str, required=True,
                       help='输出目录路径')
    parser.add_argument('--max-iterations', type=int, default=10,
                       help='最大循环次数')
    parser.add_argument('--top-n', type=int, default=3,
                       help='每次检查最大的 N 个文件')
    parser.add_argument('--report', type=str,
                       help='生成报告文件路径')
    
    args = parser.parse_args()
    
    config_path = Path(args.config)
    output_dir = Path(args.output)
    
    if not config_path.exists():
        logger.error(f"配置文件不存在：{config_path}")
        return 1
    
    if not output_dir.exists():
        logger.error(f"输出目录不存在：{output_dir}")
        return 1
    
    checker = QualityChecker(config_path, output_dir)
    checker.max_iterations = args.max_iterations
    checker.top_n = args.top_n
    
    # 执行检查
    success = checker.check_and_fix()
    
    # 生成报告
    if args.report:
        report = checker.generate_report()
        Path(args.report).write_text(report, encoding='utf-8')
        logger.info(f"报告已保存：{args.report}")
    
    return 0 if success else 1


if __name__ == '__main__':
    exit(main())
