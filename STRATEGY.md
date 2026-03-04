# 翻译质量保障策略 🎨

> **版本**: v0.2  
> **更新日期**: 2026-03-05  
> **设计理念**: 高温翻译 + 检测修复

---

## 🎯 核心策略

**保持高温翻译，让文风自然流畅，重复问题靠检测脚本修复。**

---

## ⚖️ 两种策略对比

| 策略 | 温度 | 优点 | 缺点 | 选择 |
|------|------|------|------|------|
| **低温预防** | 0.3 | 重复少 | 翻译死板、不自然 | ❌ |
| **高温 + 修复** | 0.7 | 翻译自然流畅 | 需要重试几次 | ✅ |

---

## 📋 推荐配置

### config.yaml

```yaml
translation:
  temperature: 0.7          # ✅ 保持创造性
  top_p: 0.8
  frequency_penalty: 0.0    # 不限制，靠检测修复
  
workflow:
  chunk_size: 2000
  chunk_overlap: 0
  auto_retry: true          # ✅ 启用自动重试
```

### 重试策略

```python
async def translate_chunk(chunk_id, text, translator):
    max_retries = 3
    
    for attempt in range(max_retries):
        # 始终保持高温
        translated = await translator.translate(
            text,
            temperature=0.7
        )
        
        # 检测
        result = comprehensive_check(translated)
        
        if not result['has_issues']:
            return translated
        
        # 重试时只增加提示，不降低温度
        if attempt < max_retries - 1:
            translator.set_extra_prompt("""
⚠️ 注意：
- 不要重复任何句子或段落
- 不要添加自我注释
- 保持翻译流畅自然
""")
    
    # 标记为人工审查
    return translated, needs_review=True
```

---

## 📊 成本分析

### 重试成本 vs 质量损失

| 场景 | 成本 | 影响 |
|------|------|------|
| **重试 1 次** | ~60 秒 | 可接受 |
| **重试 3 次** | ~180 秒 | 可接受 |
| **低温翻译** | 0 秒 | 整本书质量下降 |

**结论**：重试成本远低于翻译质量损失。

### 实际数据（422 个切片）

```
总切片数：422
问题切片：~10 个（2.4%）
平均重试：2 次/问题切片
额外时间：20 × 60 秒 = 20 分钟
总翻译时间：~8 小时
额外开销：~4%
```

**4% 的时间换取 100% 的翻译质量，非常值得！**

---

## 🛠️ 检测修复流程

```
翻译 (T=0.7) → 检测 → 有问题？
                      ↓ 是
                  重试 (T=0.7)
                      ↓
                  再检测 → 还有问题？
                              ↓ 是
                          再重试 (T=0.7)
                              ↓
                          还还有问题？
                              ↓ 是
                          标记人工审查
                              ↓ 否
                          保存 ✓
```

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `modules/repetition_checker.py` | 检测模块 |
| `scripts/quality_check.py` | 兜底检查脚本 |
| `config.yaml.template` | 配置模板（已更新说明） |

---

## 💡 最佳实践

1. **保持高温** - 不要为了预防重复降低温度
2. **启用重试** - 给模型第二次机会
3. **兜底检查** - 翻译完成后运行质量检查
4. **人工审查** - 极端情况手动修复

---

**维护者**: nanobot 🐈  
**许可证**: MIT
