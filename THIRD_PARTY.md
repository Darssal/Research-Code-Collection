# 第三方来源与依赖

本仓库整理已有实验脚本与工程代码。它没有复制原项目中的数据、论文附件或第三方仓库历史。

| 项目 | 依赖或上游 | 使用范围 |
| --- | --- | --- |
| FracLogGPT-Lite | [ms-swift](https://github.com/modelscope/ms-swift)、[Transformers](https://github.com/huggingface/transformers)、[PEFT](https://github.com/huggingface/peft) | 详细说明保留在该独立仓库 |
| 招聘文本分类 | [scikit-learn](https://github.com/scikit-learn/scikit-learn)、[PyTorch](https://github.com/pytorch/pytorch)、[Transformers](https://github.com/huggingface/transformers) | 文本特征、分类器与可选 BERT 模型加载；未复制其源码或模型权重 |
| memlab | [DeerFlow](https://github.com/bytedance/deer-flow)、Redis、PostgreSQL、Qdrant | 外部实验运行依赖；未包含服务数据与 DeerFlow 源码 |

memlab 原实验工程的 DeerFlow checkout 基线为 `7de94394d4295182701ffb47e938e7c39b963091`。该版本的 [MIT 许可证](https://github.com/bytedance/deer-flow/blob/7de94394d4295182701ffb47e938e7c39b963091/LICENSE) 保留 ByteDance 与 DeerFlow Authors 署名；使用外部 checkout 时应保留并遵守其许可。本仓库不会将上游许可证套用于独立整理的实验代码。

模型标识仅用于配置示例，使用者需自行核对对应模型条款、版本和运行条件。本仓库不对提供方当前资费或服务可用性作保证。
