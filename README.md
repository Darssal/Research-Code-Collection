# Research Code Collection

**Agent 多层记忆与中文文本分类实验工程。** 两个独立 Python 子项目，覆盖上下文组装、异步会话、实验有效性检查、分类基线与服务批处理。

[![Code and publication checks](https://github.com/Darssal/Research-Code-Collection/actions/workflows/checks.yml/badge.svg)](https://github.com/Darssal/Research-Code-Collection/actions/workflows/checks.yml)

[MemLab](#memlab--agent-多层记忆) · [文本分类](#招聘文本三分类) · [工程笔记](docs/ENGINEERING_NOTES.md) · [验证与来源](#验证与来源)

## MemLab / Agent 多层记忆

面向并行会话，分离近期上下文、热缓存、持久化元数据与向量检索，提供统一记忆接口和实验控制组件。

| 技术问题 | 实现机制 | 入口 |
| --- | --- | --- |
| 记忆如何放置与取回 | L0–L3 分层、重要度准入、大对象指针、异步批量写入 | [记忆管理器](projects/memlab/memlab/memory_manager/manager.py) |
| 检索内容如何进入上下文 | 相关性筛选、版本与文本去重、注入预算、直接证据绕过 | [上下文策略](projects/memlab/memlab/memory_manager/l0.py) |
| 并发会话如何保留归属 | ContextVar 隔离日志上下文，记录缓存与降级路径 | [会话日志](projects/memlab/memlab/session_logging.py) |
| 哪些运行可进入汇总 | 有效性条件、失效阶段回滚和重跑计划 | [实验控制](projects/memlab/memlab/pipeline/control_plane.py) |

`Python 3.12` · `asyncio` · `Redis` · `PostgreSQL` · `Qdrant`

[项目与安装](projects/memlab/) · [架构](projects/memlab/docs/ARCHITECTURE.md) · [53 项离线测试的覆盖范围](projects/memlab/docs/TESTING.md)

## 招聘文本三分类

识别环保、人工智能与其它招聘文本（其它在接口中使用标签 `否`），提供本地基线、可选 BERT 和外部聊天服务适配器。

- **数据与评测**：CSV / JSONL 接口、固定种子分层划分、重复文本检查；先划分再拟合 TF-IDF，按实际类别顺序对齐概率与指标。
- **服务批处理**：超时、有界重试、非临时错误快速结束、并发保序；默认预测产物只保留 ID、标签与错误状态。
- **可运行示例**：24 条新编写的合成文本，CPU 执行本地随机森林流程，16 项回归测试覆盖核心行为。

```bash
cd projects/job-text-classification
python -m pip install -e .
python -m job_text_classification demo
```

`Python` · `scikit-learn` · `TF-IDF` · `Random Forest` · `ThreadPoolExecutor`

[数据接口与运行](projects/job-text-classification/) · [分类实现](projects/job-text-classification/src/job_text_classification/baseline.py) · [服务适配](projects/job-text-classification/src/job_text_classification/http_adapter.py) · [回归测试](projects/job-text-classification/tests/test_regressions.py)

## 相关项目 / FracLogGPT-Lite

[FracLogGPT-Lite](https://github.com/Darssal/FracLogGPT-Lite) 在独立仓库维护成像测井裂缝解释的多模态实验流程：LoRA-SFT、DPO / SimPO、可恢复推理与视觉对比解码。

[项目介绍](https://github.com/Darssal/FracLogGPT-Lite) · [无 GPU 验证](https://github.com/Darssal/FracLogGPT-Lite/blob/main/docs/QUICKSTART.md) · [双分支解码](https://github.com/Darssal/FracLogGPT-Lite/blob/main/src/fraclog/vcd.py)

## 设计与验证

[工程笔记](docs/ENGINEERING_NOTES.md)连接问题、机制、小例子和测试，涵盖推理恢复、上下文与会话隔离、分类评测与失败处理。

每个子项目独立安装。分类 demo 与 MemLab 单元测试可离线运行；MemLab stub / E2E 需要另行配置基础设施。持续集成检查分类、记忆组件及公开文件边界，详见 [Actions](https://github.com/Darssal/Research-Code-Collection/actions/workflows/checks.yml)。

## 验证与来源

2026-10-18 验证记录：分类 16 项、MemLab 53 项离线测试通过。合成示例用于检查流程；BERT 训练、真实 HTTP 服务、数据库与 DeerFlow 集成、论文性能实验尚未在公开版整理中运行。

源码、配置、测试与合成示例可以公开；真实语料、论文材料、权重、运行输出和凭据保留在本地。第三方框架与模型的来源见 [THIRD_PARTY.md](THIRD_PARTY.md)，提交规则见 [CONTRIBUTING.md](CONTRIBUTING.md) 与[公开范围](docs/PUBLICATION_SCOPE.md)。
