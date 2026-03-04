# booktran 版本说明

## v0.1 MVP (当前版本)

**状态**: 🟡 开发中  
**发布日期**: 2026-03-04  
**作者**: davidanger with nanobot-354345126

### 核心功能

- ✅ 支持 7 种格式：PDF, EPUB, FB2, TXT, DOCX, HTML
- ✅ 智能切片 (2000 字符/片，无重叠)
- ✅ 单模型翻译 (OpenAI 兼容 API)
- ✅ 断点续传
- ✅ 摘要和术语管理
- ✅ EPUB 输出 (支持图片嵌入)
- ✅ 目录导航 (自动中文化)
- ✅ 章节标题翻译

### 技术架构

```
booktran/
├── booktran_skill.py     # 主入口
├── workflow.py           # 工作流编排
├── config.yaml.template  # 配置模板
├── modules/              # 核心模块
│   ├── parser.py         # 文档解析
│   ├── chunker.py        # 智能切片
│   ├── translator.py     # 翻译
│   ├── summary.py        # 摘要管理
│   ├── state_manager.py  # 断点续传
│   └── epub_manual.py    # EPUB 构建
└── utils/                # 工具函数 (归档中)
```

### 已知问题

- [ ] 摘要文档累积导致后期翻译速度下降
- [ ] 不支持 OCR 扫描版 PDF
- [ ] 不支持 MOBI/AZW3 格式
- [ ] 无 Web UI 监控

### 后续版本计划

#### v0.2 (性能优化)
- [ ] 滑动窗口摘要 (解决速度下降问题)
- [ ] 摘要压缩机制
- [ ] 章节级摘要重置

#### v1.0 (稳定版)
- [ ] 完整测试覆盖
- [ ] 性能基准测试
- [ ] 文档完善

#### v2.0 (功能扩展)
- [ ] MOBI/AZW3 支持
- [ ] OCR 扫描版 PDF 处理
- [ ] 主备模型自动切换
- [ ] 多备用模型支持
- [ ] 图片/表格/公式提取
- [ ] Web UI 进度监控

---

## 开发历史

- **2026-03-02**: 项目启动
- **2026-03-04**: v0.1 MVP 完成
- **2026-03-04**: 首次完整翻译测试 (《Insatiable Wives》29 章)

---

**GitHub**: https://github.com/davidanger/booktran  
**许可证**: MIT
