#!/usr/bin/env python3
"""
实时检测示例 - 演示如何在翻译过程中集成重复检测
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.repetition_checker import comprehensive_check

# 示例 1: 正常翻译
normal_text = """
春意弥漫在空气中。鸟儿在树间啁啾，穿梭于纤细的枝桠之间。
这是鲜花绽放、蜜蜂嗡鸣、新生命降临的季节。
在沼泽河岸旁，一只小型苇莺与其配偶筑起了一窝由细枝构成的巢穴。
"""

print("="*60)
print("示例 1: 正常翻译")
print("="*60)
result = comprehensive_check(normal_text)
print(f"发现问题：{result['has_issues']}")
print(f"问题类型：{result['issues']}")
print()

# 示例 2: 字符重复
char_repeat_text = "性、性、性、性、性、性、性、性、性、性、性、性、性"

print("="*60)
print("示例 2: 字符重复")
print("="*60)
result = comprehensive_check(char_repeat_text)
print(f"发现问题：{result['has_issues']}")
print(f"问题类型：{result['issues']}")
if 'char_repeat' in result['details']:
    print(f"详细信息：{result['details']['char_repeat']}")
print()

# 示例 3: 句子重复
sentence_repeat_text = """
在印度，不忠妻子的鼻子和阴蒂均被割除。
在印度，不忠妻子的鼻子和阴蒂均被割除。
在印度，不忠妻子的鼻子和阴蒂均被割除。
在印度，不忠妻子的鼻子和阴蒂均被割除。
在印度，不忠妻子的鼻子和阴蒂均被割除。
这是新句子。
"""

print("="*60)
print("示例 3: 句子重复")
print("="*60)
result = comprehensive_check(sentence_repeat_text)
print(f"发现问题：{result['has_issues']}")
print(f"问题类型：{result['issues']}")
if 'high_freq_sentences' in result['details']:
    for item in result['details']['high_freq_sentences']:
        print(f"  - 重复{item['count']}次：{item['sentence'][:30]}...")
print()

# 示例 4: 注释重复
note_repeat_text = """
这是一段翻译内容。
（注：原文此处有双关语）
这是另一段翻译。
（注：原文此处有双关语）
（注：原文此处有双关语）
"""

print("="*60)
print("示例 4: 注释重复")
print("="*60)
result = comprehensive_check(note_repeat_text)
print(f"发现问题：{result['has_issues']}")
print(f"问题类型：{result['issues']}")
if 'note_repeat' in result['details']:
    print(f"详细信息：{result['details']['note_repeat']}")
print()

# 示例 5: 在翻译循环中的使用示例
print("="*60)
print("示例 5: 翻译循环中的实时检测")
print("="*60)
print("""
async def translate_with_check(chunk_id, text, translator):
    '''翻译并实时检测'''
    
    # 第一次翻译
    translated = await translator.translate(text)
    
    # 实时检测
    result = comprehensive_check(translated)
    
    if result['has_issues']:
        logger.warning(f"分片 {chunk_id} 发现问题：{result['issues']}")
        
        # 重试（最多 3 次）
        for retry in range(3):
            logger.info(f"第 {retry + 1} 次重试...")
            translated = await translator.translate(
                text,
                extra_prompt="⚠️ 不要重复任何内容"
            )
            
            result = comprehensive_check(translated)
            if not result['has_issues']:
                break
        
        if result['has_issues']:
            logger.error(f"分片 {chunk_id} 重试失败，标记为人工审查")
    
    # 保存结果
    save_chunk(chunk_id, translated)
    return translated
""")
