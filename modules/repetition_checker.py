"""
重复检测模块 - 检测和修复翻译中的重复问题
"""

import re
from pathlib import Path
from typing import Tuple, List, Dict
from collections import Counter


def detect_char_repeat(text: str, min_repeat: int = 10) -> Tuple[bool, List[str]]:
    """检测连续字符重复（如：性、性、性、性...）
    
    Args:
        text: 待检测文本
        min_repeat: 最小重复次数阈值
    
    Returns:
        (是否发现重复，重复模式列表)
    """
    repeats = []
    
    # 检测单字重复（如：性性性性）
    pattern_char = r'([\u4e00-\u9fa5a-zA-Z])\1{' + str(min_repeat - 1) + r',}'
    matches = re.findall(pattern_char, text)
    if matches:
        repeats.extend([f"字符重复：'{m[0]}'" for m in set(matches)])
    
    # 检测词语重复（如：性、性、性、）
    pattern_word = r'([\u4e00-\u9fa5]{2,4}[,，、\s]*)\1{' + str(min_repeat - 1) + r',}'
    matches = re.findall(pattern_word, text)
    if matches:
        repeats.extend([f"词语重复：'{m[0].strip()}'" for m in set(matches)])
    
    # 特殊检测：单个字 + 标点重复（如：性、性、性、）
    pattern_single = r'([\u4e00-\u9fa5])[,，、]\1[,，、]'
    matches = re.findall(pattern_single, text)
    if matches:
        # 计算重复次数
        for char in set(matches):
            count = text.count(f'{char}、') + text.count(f'{char}，') + text.count(f'{char},')
            if count >= min_repeat:
                repeats.append(f"单字重复：'{char}' 重复{count}次")
    
    return len(repeats) > 0, repeats


def detect_high_freq_sentences(text: str, min_count: int = 5) -> Tuple[bool, List[Dict]]:
    """检测高频短句（即使总重复率不高，但单句重复次数过多）
    
    Args:
        text: 待检测文本
        min_count: 最小重复次数
    
    Returns:
        (是否发现重复，高频句子列表)
    """
    sentences = re.split(r'[。！？.!?]+', text)
    sentences = [s.strip() for s in sentences if 5 < len(s.strip()) < 50]  # 短句
    counts = Counter(sentences)
    
    high_freq = [
        {'sentence': s, 'count': c}
        for s, c in counts.items()
        if c >= min_count
    ]
    
    return len(high_freq) > 0, high_freq


def detect_sentence_repeat(text: str, threshold: float = 0.2) -> Tuple[bool, Dict]:
    """检测句子级别重复
    
    Args:
        text: 待检测文本
        threshold: 重复率阈值（0.2 = 20% 内容重复）
    
    Returns:
        (是否超过阈值，统计信息)
    """
    # 按句号、问号、感叹号分割句子
    sentences = re.split(r'[。！？.!?]+', text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 10]  # 过滤太短的句子
    
    if not sentences:
        return False, {'total_sentences': 0, 'repeated_sentences': 0, 'repetition_rate': 0}
    
    # 统计句子出现次数
    sentence_counts = Counter(sentences)
    
    # 计算重复句子的总长度
    repeated_sentences = [s for s, c in sentence_counts.items() if c > 1]
    repeated_len = sum(len(s) for s in repeated_sentences)
    total_len = sum(len(s) for s in sentences)
    
    repetition_rate = repeated_len / total_len if total_len > 0 else 0
    
    stats = {
        'total_sentences': len(sentences),
        'unique_sentences': len(sentence_counts),
        'repeated_sentences': len(repeated_sentences),
        'repetition_rate': repetition_rate,
        'repeated_examples': repeated_sentences[:3]  # 前 3 个重复句子示例
    }
    
    return repetition_rate > threshold, stats


def detect_paragraph_repeat(text: str, threshold: float = 0.2) -> Tuple[bool, Dict]:
    """检测段落级别重复
    
    Args:
        text: 待检测文本
        threshold: 重复率阈值
    
    Returns:
        (是否超过阈值，统计信息)
    """
    # 按空行分割段落
    paragraphs = text.split('\n\n')
    paragraphs = [p.strip() for p in paragraphs if len(p.strip()) > 50]  # 过滤太短的段落
    
    if not paragraphs:
        return False, {'total_paragraphs': 0, 'repeated_paragraphs': 0, 'repetition_rate': 0}
    
    # 统计段落出现次数
    para_counts = Counter(paragraphs)
    
    # 计算重复段落的总长度
    repeated_paras = [p for p, c in para_counts.items() if c > 1]
    repeated_len = sum(len(p) for p in repeated_paras)
    total_len = sum(len(p) for p in paragraphs)
    
    repetition_rate = repeated_len / total_len if total_len > 0 else 0
    
    stats = {
        'total_paragraphs': len(paragraphs),
        'unique_paragraphs': len(para_counts),
        'repeated_paragraphs': len(repeated_paras),
        'repetition_rate': repetition_rate,
        'repeated_examples': repeated_paras[:2]  # 前 2 个重复段落示例
    }
    
    return repetition_rate > threshold, stats


def detect_self_note_repeat(text: str) -> Tuple[bool, List[str]]:
    """检测自我注释重复（如：注：... 注：... 注：...）
    
    Args:
        text: 待检测文本
    
    Returns:
        (是否发现重复，重复模式列表)
    """
    repeats = []
    
    # 检测"注："重复
    note_pattern = r'（注：[^）]+）'
    notes = re.findall(note_pattern, text)
    note_counts = Counter(notes)
    repeated_notes = [n for n, c in note_counts.items() if c > 1]
    
    if len(repeated_notes) > 0:
        repeats.append(f"注释重复：{len(repeated_notes)} 个注释重复出现")
    
    # 检测"重新翻译"、"最终确认"等标记重复
    marker_pattern = r'\*\*[^*]+(重新翻译 | 最终确认 | 校对)[^*]+\*\*'
    markers = re.findall(marker_pattern, text)
    if len(markers) > 1:
        repeats.append(f"翻译标记重复：{len(markers)} 个翻译标记")
    
    return len(repeats) > 0, repeats


def detect_volume_anomaly(file_path: Path, expected_max_size: int = 50000) -> Tuple[bool, Dict]:
    """检测文件体积异常
    
    Args:
        file_path: 文件路径
        expected_max_size: 预期最大字节数
    
    Returns:
        (是否异常，统计信息)
    """
    actual_size = file_path.stat().st_size
    
    stats = {
        'file_size': actual_size,
        'expected_max': expected_max_size,
        'ratio': actual_size / expected_max_size if expected_max_size > 0 else 0
    }
    
    return actual_size > expected_max_size, stats


def comprehensive_check(text: str, file_path: Path = None) -> Dict:
    """综合重复检查
    
    Args:
        text: 待检测文本
        file_path: 文件路径（可选，用于体积检测）
    
    Returns:
        检查结果字典
    """
    results = {
        'has_issues': False,
        'issues': [],
        'details': {}
    }
    
    # 1. 字符重复检测
    char_repeat, char_repeats = detect_char_repeat(text)
    if char_repeat:
        results['has_issues'] = True
        results['issues'].append('字符重复')
        results['details']['char_repeat'] = char_repeats
    
    # 2. 高频短句检测（新增）
    high_freq, high_freq_list = detect_high_freq_sentences(text, min_count=5)
    if high_freq:
        results['has_issues'] = True
        results['issues'].append('高频短句重复')
        results['details']['high_freq_sentences'] = high_freq_list
    
    # 3. 句子重复检测
    sent_repeat, sent_stats = detect_sentence_repeat(text)
    if sent_repeat:
        results['has_issues'] = True
        results['issues'].append('句子重复')
        results['details']['sentence_repeat'] = sent_stats
    
    # 4. 段落重复检测
    para_repeat, para_stats = detect_paragraph_repeat(text)
    if para_repeat:
        results['has_issues'] = True
        results['issues'].append('段落重复')
        results['details']['paragraph_repeat'] = para_stats
    
    # 5. 自我注释重复检测
    note_repeat, note_repeats = detect_self_note_repeat(text)
    if note_repeat:
        results['has_issues'] = True
        results['issues'].append('注释重复')
        results['details']['note_repeat'] = note_repeats
    
    # 6. 体积异常检测
    if file_path:
        vol_anomaly, vol_stats = detect_volume_anomaly(file_path)
        if vol_anomaly:
            results['has_issues'] = True
            results['issues'].append('体积异常')
            results['details']['volume_anomaly'] = vol_stats
    
    return results


def check_chunk_file(chunk_path: Path) -> Dict:
    """检查单个切片文件
    
    Args:
        chunk_path: 切片文件路径
    
    Returns:
        检查结果
    """
    if not chunk_path.exists():
        return {'error': f'文件不存在：{chunk_path}'}
    
    content = chunk_path.read_text(encoding='utf-8')
    results = comprehensive_check(content, chunk_path)
    results['chunk_id'] = chunk_path.stem
    results['file_size'] = chunk_path.stat().st_size
    
    return results


def check_top_chunks(output_dir: Path, top_n: int = 3) -> List[Dict]:
    """检查体积最大的 N 个切片文件
    
    Args:
        output_dir: 输出目录（包含 chunks_translated 子目录）
        top_n: 检查前 N 个最大的文件
    
    Returns:
        检查结果列表
    """
    chunks_dir = output_dir / 'chunks_translated'
    if not chunks_dir.exists():
        return [{'error': f'目录不存在：{chunks_dir}'}]
    
    # 按体积排序
    chunk_files = sorted(
        chunks_dir.glob('chunk_*.md'),
        key=lambda f: f.stat().st_size,
        reverse=True
    )[:top_n]
    
    results = []
    for chunk_path in chunk_files:
        result = check_chunk_file(chunk_path)
        results.append(result)
    
    return results


if __name__ == '__main__':
    # 测试示例
    test_text = "性、性、性、性、性、性、性、性、性、性、性"
    has_repeat, repeats = detect_char_repeat(test_text)
    print(f"字符重复检测：{has_repeat}, {repeats}")
    
    test_text2 = "你好世界。你好世界。你好世界。这是新句子。"
    has_repeat, stats = detect_sentence_repeat(test_text2)
    print(f"句子重复检测：{has_repeat}, {stats}")
