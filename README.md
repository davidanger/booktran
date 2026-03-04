# booktran 📚

> **版本**: v0.1 MVP  
> **状态**: 🟡 开发中  
> **许可证**: MIT  
> **作者**: davidanger with nanobot-354345126

**多模态文档翻译工具** - 将英文 PDF/EPUB 等电子书翻译为中文 EPUB

> **💡 智能体技能**: 本项目是一个**AI 智能体技能**，在 [nanobot](https://github.com/nanobot) 平台上开发和测试，理论上兼容其他智能体框架。可以作为独立工具使用，也可以集成到智能体系统中。

---

## 🎯 功能特性

- ✅ **7 种格式支持**: PDF, EPUB, FB2, TXT, DOCX, HTML
- ✅ **智能切片**: 2000 字符/片，保持上下文连贯
- ✅ **单模型翻译**: OpenAI 兼容 API
- ✅ **断点续传**: 意外中断可继续
- ✅ **摘要管理**: 自动维护术语和上下文
- ✅ **EPUB 输出**: 标准电子书格式，支持图片嵌入
- ✅ **目录导航**: 自动生成中文目录

---

## 🚀 快速开始

### 1. 克隆仓库

```bash
git clone https://github.com/davidanger/booktran.git
cd booktran
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置

复制配置模板并修改：

```bash
cp config.yaml.template config.yaml
```

编辑 `config.yaml`，填写你的 API 配置：

```yaml
translation:
  base_url: "https://your-api-base-url.com/v1"
  api_key: "sk-your-api-key-here"
  model: "your-model-name"
```

### 4. 使用

#### 方式 1: 直接运行工作流

```bash
python3 workflow.py
```

#### 方式 2: nanobot 集成

如果使用 nanobot，发送文件后回复：
```
@booktran translate
```

#### 方式 3: Python 调用

```python
from workflow import TranslationWorkflow

workflow = TranslationWorkflow(
    config_path="config.yaml",
    workspace_dir="./output"
)
result = await workflow.run("input/book.epub")
```

---

## 📋 使用方式

### 作为独立工具

```bash
# 运行工作流
python3 workflow.py

# 或作为脚本调用
python3 -c "from workflow import TranslationWorkflow; print('OK')"
```

### 作为 nanobot Skill

| 命令 | 说明 | 示例 |
|------|------|------|
| `@booktran translate <文件>` | 翻译文件 | `@booktran translate book.epub` |
| `@booktran config` | 查看配置 | `@booktran config` |
| `@booktran status` | 查看任务状态 | `@booktran status` |
| `@booktran help` | 帮助信息 | `@booktran help` |

---

## ⚙️ 配置说明

### 配置文件：`config.yaml`

```yaml
# 翻译模型配置
translation:
  base_url: "https://your-api-base-url.com/v1"
  api_key: "sk-your-api-key-here"
  model: "your-model-name"
  timeout: 120
  max_retries: 3

# 工作流配置
workflow:
  target_lang: "zh"
  source_lang: "en"
  chunk_size: 2000
  chunk_overlap: 0
  auto_retry: true

# 输出配置
output:
  save_intermediate: true
  output_dir: "./output"
```

### 配置项说明

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `base_url` | string | - | API Base URL (兼容 OpenAI 格式) |
| `api_key` | string | - | API Key |
| `model` | string | - | 模型名称 |
| `timeout` | int | 120 | 请求超时时间 (秒) |
| `max_retries` | int | 3 | 最大重试次数 |
| `chunk_size` | int | 2000 | 切片大小 (字符数) |
| `chunk_overlap` | int | 0 | 切片重叠 (字符数)，建议为 0 |
| `target_lang` | string | "zh" | 目标语言 |
| `source_lang` | string | "en" | 源语言 |

---

## 📁 目录结构

```
booktran/
├── booktran_skill.py     # 主入口（nanobot 集成）
├── workflow.py           # 工作流编排
├── config.yaml.template  # 配置模板
├── requirements.txt      # 依赖清单
├── LICENSE               # MIT 许可证
├── README.md             # 本文件
├── .gitignore            # Git 忽略规则
├── modules/              # 核心模块
│   ├── __init__.py
│   ├── parser.py         # 文档解析 (PDF, EPUB, etc.)
│   ├── chunker.py        # 智能切片
│   ├── translator.py     # 翻译 (LLM API)
│   ├── summary.py        # 摘要管理
│   ├── state_manager.py  # 断点续传
│   ├── structure.py      # 文档结构
│   ├── epub_manual.py    # EPUB 构建 (手动)
│   └── epub_builder.py   # EPUB 构建 (自动)
├── _archive/             # 归档文件 (开发历史，不上传)
└── output/               # 输出目录 (git 忽略)
```

---

## 🔧 开发

### 依赖安装

```bash
pip install -r requirements.txt
```

### 测试

```bash
# 测试解析模块
python3 -c "from modules.parser import parse_document; print('OK')"

# 测试工作流
python3 workflow.py
```

### 添加新格式

1. 在 `modules/parser.py` 添加解析函数
2. 更新 `PARSER_MAP` 映射
3. 更新 `requirements.txt`

---

## 📌 后续版本 (v2.0+)

- [ ] MOBI/AZW3 支持
- [ ] OCR 扫描版 PDF 处理
- [ ] 主备模型自动切换
- [ ] 多备用模型支持
- [ ] 图片/表格/公式提取
- [ ] Web UI 进度监控

---

## ⚠️ 注意事项

1. **大文件**: 建议文件大小 < 50MB
2. **API 限流**: 注意翻译 API 的调用频率限制
3. **扫描版 PDF**: v0.1 不支持 OCR，需要文本版 PDF
4. **内存占用**: 大文件可能占用较多内存
5. **配置安全**: 不要将 `config.yaml` 提交到 Git（已加入 .gitignore）

---

## 🐛 故障排查

### 配置问题

```bash
# 检查配置文件
cat config.yaml

# 重新配置
cp config.yaml.template config.yaml
```

### 依赖问题

```bash
# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

### 模块导入问题

```bash
# 测试模块导入
python3 -c "from modules.parser import parse_document; print('OK')"
python3 -c "from workflow import TranslationWorkflow; print('OK')"
```

### 翻译失败

1. 检查 API Key 是否有效
2. 检查网络连接
3. 查看错误日志

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

**开发团队**: davidanger with nanobot-354345126  
**版本**: v0.1 MVP  
**更新时间**: 2026-03-04  
**GitHub**: https://github.com/davidanger/booktran
