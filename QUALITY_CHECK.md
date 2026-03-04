# 翻译质量保障体系 🛡️

> **版本**: v0.1  
> **最后更新**: 2026-03-05

本文档说明 booktran 的翻译质量保障机制，包括预防措施、实时检测和兜底检查。

---

## 📋 目录

1. [问题类型](#问题类型)
2. [三层防御体系](#三层防御体系)
3. [使用方法](#使用方法)
4. [配置参数](#配置参数)
5. [故障排查](#故障排查)

---

## 问题类型

翻译过程中可能出现的重复问题：

| 类型 | 示例 | 检测方法 |
|------|------|----------|
| **字符重复** | 性、性、性、性、性... | `detect_char_repeat()` |
| **高频短句** | 某句子重复 10+ 次 | `detect_high_freq_sentences()` |
| **句子重复** | 重复率 > 20% | `detect_sentence_repeat()` |
| **段落重复** | 某段落重复多次 | `detect_paragraph_repeat()` |
| **注释重复** | （注：...）重复出现 | `detect_self_note_repeat()` |
| **体积异常** | 文件 > 50KB | `detect_volume_anomaly()` |

---

## 三层防御体系

### 第一层：预防（翻译前）

**目标**: 防止重复问题发生

```python
# 1. 优化切片逻辑
- 确保切片边界在完整句子处
- 无重叠切片（overlap=0）
- 每个切片 2000 字符左右

# 2. 优化 Summary 管理
- 使用滑动窗口，避免累积重复
- 每章重置 summary
- 保持 summary 简洁

# 3. 增强提示词
SYSTEM_PROMPT = """
⚠️ 重要要求：
1. 不要重复任何句子或段落
2. 不要添加自我注释
3. 不要重复任何词语
4. 保持翻译流畅自然
"""
```

### 第二层：实时检测（翻译每个切片时）

**目标**: 发现问题立即重试，不进入下一步

```python
# workflow.py 中的翻译循环
for chunk in chunks:
    translated = await translate(chunk)
    
    # 立即检查重复
    from modules.repetition_checker import comprehensive_check
    result = comprehensive_check(translated)
    
    if result['has_issues']:
        logger.warning(f"分片 {chunk_id} 发现问题：{result['issues']}")
        # 立即重试（最多 3 次）
        translated = await translate(chunk, retry=True)
    
    save_chunk(chunk_id, translated)
```

**检测指标**:
- 字符重复：≥ 10 次
- 高频短句：≥ 5 次
- 句子重复率：> 20%
- 段落重复率：> 20%

### 第三层：兜底检查（所有翻译完成后）

**目标**: 捕获遗漏问题，批量修复

```bash
# 运行兜底检查
python scripts/quality_check.py --output output/full_20260304_152325
```

**工作流程**:
1. 按体积排序所有切片
2. 检查最大的 3 个文件
3. 发现问题 → 重新翻译
4. 循环检查（最多 10 次）
5. 生成质量报告

---

## 使用方法

### 单独检查一个切片

```python
from modules.repetition_checker import check_chunk_file
from pathlib import Path

result = check_chunk_file(Path('chunks_translated/chunk_014.md'))

print(f"发现问题：{result['has_issues']}")
print(f"问题类型：{result['issues']}")
```

### 检查最大的 N 个切片

```python
from modules.repetition_checker import check_top_chunks
from pathlib import Path

results = check_top_chunks(Path('output/full_20260304_152325'), top_n=5)

for r in results:
    if r['has_issues']:
        print(f"⚠️ {r['chunk_id']}: {r['issues']}")
```

### 运行完整兜底检查

```bash
# 基本用法
python scripts/quality_check.py --output output/full_20260304_152325

# 指定配置文件
python scripts/quality_check.py \
  --config config.yaml \
  --output output/full_20260304_152325

# 生成报告
python scripts/quality_check.py \
  --output output/full_20260304_152325 \
  --report quality_report.md

# 自定义参数
python scripts/quality_check.py \
  --output output/full_20260304_152325 \
  --max-iterations 15 \
  --top-n 5
```

---

## 配置参数

### 检测阈值（modules/repetition_checker.py）

```python
# 字符重复检测
min_repeat = 10  # 最小重复次数

# 句子重复检测
threshold = 0.2  # 重复率阈值（20%）

# 段落重复检测
threshold = 0.2  # 重复率阈值（20%）

# 高频短句检测
min_count = 5  # 最小重复次数

# 体积异常检测
expected_max_size = 50000  # 最大字节数（50KB）
```

### 兜底检查参数（scripts/quality_check.py）

```python
max_iterations = 10  # 最大循环次数
top_n = 3           # 每次检查最大的 N 个文件
```

### 调整阈值

如果误报太多（正常切片被标记为问题）：
- 提高 `threshold`（如 0.2 → 0.3）
- 提高 `min_repeat`（如 10 → 15）
- 提高 `min_count`（如 5 → 8）

如果漏报太多（问题切片没检测到）：
- 降低 `threshold`（如 0.2 → 0.15）
- 降低 `min_repeat`（如 10 → 8）
- 降低 `min_count`（如 5 → 3）

---

## 故障排查

### 问题切片没检测到

1. **检查阈值设置**
   ```python
   # 降低阈值
   threshold = 0.15  # 从 0.2 降低
   ```

2. **增加检测维度**
   ```python
   # 添加新的检测函数
   def detect_new_pattern(text):
       ...
   ```

3. **手动检查日志**
   ```bash
   # 查看详细检测结果
   python -c "
   from modules.repetition_checker import check_chunk_file
   from pathlib import Path
   import json
   
   result = check_chunk_file(Path('chunks_translated/chunk_XXX.md'))
   print(json.dumps(result, indent=2, ensure_ascii=False))
   "
   ```

### 正常切片被误报

1. **提高阈值**
2. **检查切片内容** - 可能原文本身就重复（如诗歌、列表）
3. **添加白名单** - 某些章节类型可以跳过检测

### 重新翻译后仍有问题

1. **检查模型** - 换用更强大的模型
2. **优化提示词** - 增加防重复指令权重
3. **降低温度参数** - `temperature=0.3` 减少随机性
4. **人工介入** - 手动修复极端情况

---

## 性能优化建议

### 实时检测性能

```python
# 优化：只在翻译完成后检测一次
# 不要：每生成 100 字检测一次

# 优化：使用更高效的正则表达式
# 避免：过于复杂的模式匹配
```

### 兜底检查性能

```python
# 优化：只检查 Top N 个文件
# 不要：每次检查所有 400+ 个切片

# 优化：并行检查
import asyncio
results = await asyncio.gather(
    check_chunk_file(chunk1),
    check_chunk_file(chunk2),
    check_chunk_file(chunk3)
)
```

---

## 最佳实践

1. **优先预防** - 优化切片和 summary 比事后修复更重要
2. **实时检测** - 问题越早发现，修复成本越低
3. **合理阈值** - 根据实际数据调整，不要盲目使用默认值
4. **记录问题** - 将问题切片保存到 `_archive/` 用于分析
5. **持续改进** - 定期回顾问题切片，优化检测算法

---

## 相关文件

| 文件 | 说明 |
|------|------|
| `modules/repetition_checker.py` | 核心检测模块 |
| `scripts/quality_check.py` | 兜底检查脚本 |
| `workflow.py` | 集成实时检测 |

---

**维护者**: nanobot 🐈  
**许可证**: MIT
