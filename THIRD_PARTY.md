# 来源与第三方依赖

当前仓库是索引与工程说明。历史 Collection 整理过 MemLab 与招聘分类工程；它们的当前源码和依赖说明已迁入独立仓库，未复制原实验数据、论文附件或第三方 Git 历史。

| 项目 | 当前来源与依赖说明 |
| --- | --- |
| FracLogGPT-Lite | [项目说明与依赖来源](https://github.com/Darssal/FracLogGPT-Lite/blob/main/README.md)：ms-swift、Transformers、PEFT 等外部能力 |
| MemLab | [THIRD_PARTY](https://github.com/Darssal/MemLab/blob/main/THIRD_PARTY.md)：DeerFlow、Redis、PostgreSQL、Qdrant 与 LongMemEval 数据来源边界 |
| Recruitment Text Classification | [THIRD_PARTY](https://github.com/Darssal/Recruitment-Text-Classification/blob/main/THIRD_PARTY.md)：scikit-learn、NumPy、joblib、可选 PyTorch / Transformers；无上游模型文件 |
| JSP UI Prototype | [原有来源说明](https://github.com/Darssal/JSP-UI-Prototype/blob/main/docs/LEGACY_JSP.md)：保留 [CodePen — danielkvist / LYNVyPL](https://codepen.io/danielkvist/pen/LYNVyPL) 的登录动画参考地址 |

MemLab 原实验使用的 DeerFlow 基线为 `7de94394d4295182701ffb47e938e7c39b963091`。其 [MIT 许可证](https://github.com/bytedance/deer-flow/blob/7de94394d4295182701ffb47e938e7c39b963091/LICENSE) 保留 ByteDance Ltd. 与 DeerFlow Authors 署名；外部 checkout 应继续遵守该许可。LongMemEval 的下载内容和数据许可证需另行核验，当前索引不携带数据。

各工程未因迁移而获得新的统一许可证；本索引不将上游许可证套用于整理代码，也不把参考动画或框架能力宣称为个人原创。模型和服务的版本、许可及运行条件应在使用时核对。
