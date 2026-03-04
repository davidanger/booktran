# booktran Skill 📚

> **版本**: v0.1 MVP  
> **状态**: 🟡 开发中  
> **许可证**: MIT  
> **作者**: davidanger with nanobot-354345126

**多模态文档翻译工具** - 将英文 PDF/EPUB 等电子书翻译为中文 EPUB

---

## 🎯 功能

- ✅ 支持 7 种格式：PDF, EPUB, FB2, TXT, DOCX, HTML
- ✅ 智能切片 (2000 字符/片)
- ✅ 单模型翻译 (OpenAI 兼容 API)
- ✅ 断点续传
- ✅ 摘要和术语管理
- ✅ EPUB 输出 (支持图片嵌入)
- ✅ 目录导航 (自动中文化)

---

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /path/to/booktran
pip install -r requirements.txt
```

### 2. 配置 (首次使用)

```bash
cp config.yaml.template config.yaml
# 编辑 config.yaml，填写你的 API 配置
```

### 3. 开始翻译

```bash
python3 booktran_skill.py input/book.epub
```

---

## 📋 命令列表

| 命令 | 说明 |
|------|------|
| `python3 booktran_skill.py <文件>` | 翻译文件 |
| `python3 booktran_skill.py --help` | 帮助信息 |

---

## ⚙️ 配置

配置文件：`config.yaml` (从 `config.yaml.template` 复制)

```yaml
# 翻译模型配置
translation:
  base_url: "https://your-api-base-url.com/v1"
  api_key: "sk-your-api-key-here"
  model: "your-model-name"
  timeout: 120

# 工作流配置
workflow:
  target_lang: "zh"
  source_lang: "en"
  chunk_size: 2000
  chunk_overlap: 0
```

---

## 📁 目录结构

```
booktran/
├── booktran_skill.py     # 主入口
├── workflow.py           # 工作流编排
├── config.yaml.template  # 配置模板
├── requirements.txt      # 依赖
├── modules/              # 核心模块
│   ├── parser.py         # 文档解析
│   ├── chunker.py        # 智能切片
│   ├── translator.py     # 翻译
│   ├── summary.py        # 摘要管理
│   ├── state_manager.py  # 断点续传
│   └── epub_builder.py   # EPUB 构建
├── utils/                # 工具函数
└── output/               # 输出目录 (git 忽略)
```

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

1. **配置安全**: 不要将 `config.yaml` 提交到 Git
2. **大文件**: 建议文件大小 < 50MB
3. **API 限流**: 注意翻译 API 的调用频率限制
4. **扫描版 PDF**: v0.1 不支持 OCR，需要文本版 PDF

---

## 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

**开发团队**: davidanger with nanobot-354345126  
**版本**: v0.1 MVP  
**GitHub**: https://github.com/davidanger/booktran
