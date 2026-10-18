# MemLab / Agent 多层记忆与实验控制

面向并行 Agent 会话，将近期上下文、热缓存、持久化元数据与向量检索组织为统一记忆接口。提供上下文预算与去重、分层放置、异步会话记录和实验有效性检查。

[架构](docs/ARCHITECTURE.md) · [核心记忆策略](memlab/memory_manager/manager.py) · [实验控制](memlab/pipeline/control_plane.py) · [设计取舍](../../docs/ENGINEERING_NOTES.md) · [离线测试](docs/TESTING.md)

## 可以从代码中查看的能力

- **上下文与记忆分层**：L0 上下文预算、L1 Redis 缓存、L2 Postgres 元数据与 Qdrant 检索，以及可选 L3 对象存储。
- **记忆策略**：准入和放置、直接证据识别、检索注入预算、L3 指针化，以及服务不可用时的降级记录。
- **运行记录**：manifest、事件日志、模型配置一致性检查，以及有效性门禁。未通过检查的运行会被汇总逻辑排除。
- **实验入口**：合成语料/访问轨迹生成器、stub runner、服务 microbench 和 E2E runner。stub runner 仍需要外部基础设施；离线体验请先运行测试。

## 最短阅读与验证路径

需要 Python 3.12 或更新版本。在本目录执行：

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

测试使用临时目录和构造的样例，不需要模型、数据集、在线 API 或启动数据库。服务集成、Docker 镜像、真实模型调用和性能实验没有在这次公开版整理中运行，具体边界见 [测试说明](docs/TESTING.md)。

建议阅读 [记忆管理器](memlab/memory_manager/manager.py)、[运行控制](memlab/pipeline/control_plane.py)、[上下文组装](memlab/memory_manager/l0.py)，再看相应 [单元测试](tests/)。[架构说明](docs/ARCHITECTURE.md) 描述各层职责；[环境配置](docs/SETUP.md) 给出外部服务的接入方式。

## 上游与公开范围

公开版本提供源码、配置和离线测试；真实对话、论文数据、实验输出与模型凭据保留在本地。性能比较需另行配置服务与数据并完成实验，具体状态见[测试边界](docs/TESTING.md)。

DeerFlow 来自 [ByteDance / deer-flow](https://github.com/bytedance/deer-flow)，本项目的适配参考固定版本 `7de94394d4295182701ffb47e938e7c39b963091`。公开版没有复制该上游源码，外部 checkout 和依赖需要自行准备。适配代码不代表对该上游项目的全部实现负责。

基准适配器只保留 LongMemEval 的准备脚本和 profile 判断逻辑；下载仅在显式运行该脚本时发生。使用数据集时应先核对来源及使用条件。原工作区的历史实验矩阵、论文汇报脚本和实验结论不属于本子工程。

此整理版暂未添加新的源码许可证；第三方材料仍遵循其原有许可证。详见 [第三方说明](THIRD_PARTY.md)。
