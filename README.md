# Research Project Index

公开研究工程的导航与设计笔记。每个项目在各自独立仓库维护源码、安装说明、测试和来源；本仓库只维护索引与跨项目工程说明。

[![Index and publication checks](https://github.com/Darssal/Research-Code-Collection/actions/workflows/checks.yml/badge.svg)](https://github.com/Darssal/Research-Code-Collection/actions/workflows/checks.yml)

## Canonical Repositories

| Project | 实现与当前范围 | 入口 |
| --- | --- | --- |
| **FracLogGPT-Lite** | 成像测井裂缝解释的多模态实验流程：LoRA-SFT、DPO / SimPO、可恢复推理和视觉对比解码。公开 4B 实验工程与论文 Qwen2.5-VL 7B 设置分别说明。 | [Repository](https://github.com/Darssal/FracLogGPT-Lite) · [Quickstart](https://github.com/Darssal/FracLogGPT-Lite/blob/main/docs/QUICKSTART.md) |
| **MemLab** | Agent L0–L3 多层记忆、上下文注入、异步会话归属与运行有效性检查。离线测试与真实基础设施 / 模型实验分开验证。 | [Repository](https://github.com/Darssal/MemLab) · [Architecture](https://github.com/Darssal/MemLab/blob/main/docs/ARCHITECTURE.md) · [Testing](https://github.com/Darssal/MemLab/blob/main/docs/TESTING.md) |
| **Recruitment Text Classification** | 中文招聘文本三分类：TF-IDF / 随机森林、可选 BERT 与有界 HTTP 适配。24 条虚构样例用于流程验证；未实现论文完整 RAG 链路。 | [Repository](https://github.com/Darssal/Recruitment-Text-Classification) · [Engineering Notes](https://github.com/Darssal/Recruitment-Text-Classification/blob/main/docs/ENGINEERING_NOTES.md) |
| **JSP UI Prototype** | 早期 JSP 界面和参考登录动画的独立存档。保留 13 个页面与 CodePen 来源；业务页多为占位，没有认证、数据库或 Java 业务后端。 | [Repository](https://github.com/Darssal/JSP-UI-Prototype) · [Scope and Provenance](https://github.com/Darssal/JSP-UI-Prototype/blob/main/docs/LEGACY_JSP.md) |

## Engineering Notes

[工程实现与设计取舍](docs/ENGINEERING_NOTES.md)连接问题、机制、小例子和验证入口，覆盖阶段恢复、同步解码、上下文预算、会话隔离、分类划分与批处理失败。所有源码链接指向对应独立仓库。

安装、运行和贡献代码请进入项目仓库。各工程的单元测试检查代码行为；合成样例、离线检查或原型完整性检查均不能替代论文效果复现、真实服务集成或后端功能验证。

## Migration and Maintenance

2026-10-19，MemLab 与分类工程从已经公开去敏的 Collection 提交 `8f143f67598f88fbb8a16d599a7f3d17c623d281` 建立独立维护入口。本仓库当前分支移除两份项目源码；原有文件仍可在 [Git 历史](https://github.com/Darssal/Research-Code-Collection/tree/8f143f67598f88fbb8a16d599a7f3d17c623d281/projects) 中追溯。后续改动只提交到独立仓库，历史快照不作为第二份维护入口。

JSP 原型从个人主页已公开的 Git blobs 迁移，来源记录保留在其独立仓库。FracLogGPT-Lite 已单独维护，本次未复制或重命名。

本仓库 CI 检查索引结构、文档链接、公开文件边界及实际 Git index，不安装或执行其他项目。源码和真实数据不迁回本索引。[贡献规则](CONTRIBUTING.md)、[公开范围](docs/PUBLICATION_SCOPE.md)与[来源说明](THIRD_PARTY.md)约束后续维护。
