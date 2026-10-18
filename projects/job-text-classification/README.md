# 招聘文本三分类 / 本地基线与服务批处理

识别环保、人工智能与其它招聘文本（接口标签分别为 `环保`、`人工智能`、`否`），提供中文字符 TF-IDF + 随机森林、可选 BERT 基线，以及外部聊天服务的 HTTP 适配器。默认示例仅在 CPU 上处理 24 条新编写的虚构文本，无需原始语料、模型权重、GPU 或 API。

核心实现包括训练词表隔离、固定标签概率对齐、预测输出最小化，以及带超时、有界重试和并发保序的外部服务批处理。

[快速运行](#快速运行) · [数据与基线](#数据接口与本地基线) · [HTTP 适配](#可选-http-服务适配) · [设计取舍](../../docs/ENGINEERING_NOTES.md)

## 快速运行

在本子目录运行以下命令，推荐 Python 3.10 或更新版本：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
python -m job_text_classification demo
python -m unittest discover -s tests -v
```

macOS/Linux 激活环境使用 `source .venv/bin/activate`。直接执行 `python -m job_text_classification` 同样进入离线 demo。输出标明 `synthetic_fixture`、`held_out_validation` 和 `paper_metrics: false`；虚构文本上的指标只验证流程，不用于解释真实岗位分类质量。

## 数据接口与本地基线

输入支持 UTF-8 CSV 或 JSONL，使用 `text`、`label` 两个字段，可提供 `record_id`。标签固定为 `环保`、`人工智能`、`否`。训练要求标签齐全；预测时 `label` 可省略。缺失 ID 时按输入顺序生成 `row-1` 等 ID，重复 ID、空文本和未知标签会报错。

以下示例完全虚构：

```json
{"record_id":"example-1","text":"虚构岗位：维护污水治理设备。","label":"环保"}
```

内置合成文件位于 `src/job_text_classification/examples/synthetic_jobs.jsonl`。用户自行准备的数据放入忽略目录 `data/`：

```powershell
python -m job_text_classification train --input data/jobs.jsonl --model-output outputs/rf.joblib
python -m job_text_classification predict --input data/new_jobs.csv --model outputs/rf.joblib --output outputs/predictions.jsonl
```

训练先按固定种子进行分层划分，再仅在训练文本上拟合 TF-IDF。每类至少需要两条记录；标准化后重复的文本会被拒绝，避免同一文本同时进入训练与验证。字符二至四元组使中文示例无需额外分词器。验证集用于流程检查，正式研究仍需独立测试集及领域标注方案。

预测结果使用固定标签顺序，并按分类器实际 `classes_` 对齐概率列。JSONL 输出默认只含记录 ID、可选真实标签、预测标签、状态和概率；不包含原文。训练后的模型及输出均在 `.gitignore` 范围内。只加载自己生成或可信来源的 joblib 模型文件。

## 可选 BERT

```powershell
python -m pip install -e ".[bert]"
python -m job_text_classification bert-train --input data/jobs.jsonl --model-name models/bert-base-chinese --model-output outputs/bert --epochs 1
python -m job_text_classification bert-predict --input data/new_jobs.jsonl --model outputs/bert --output outputs/bert_predictions.jsonl
```

默认仅查找本机已有的模型与缓存，设备默认为 CPU。确实需要从模型平台下载时，在 `bert-train` 中显式添加 `--allow-model-download`，并自行评估网络、磁盘及算力需求。训练保存最终轮次到指定目录，预测从同一目录加载，模型配置中保存固定标签映射。此整理版没有实际下载、训练或评测 BERT，不能由代码存在推断其性能。

## 可选 HTTP 服务适配

仅 `http` 子命令会将输入文本发送到配置的服务。运行前自行配置环境变量 `JOB_CLASSIFIER_API_URL` 和 `JOB_CLASSIFIER_API_KEY`；`.env.example` 只包含空值模板，程序不会自动加载 `.env`。服务需接收 `POST` JSON `{"message":"提示及输入文本","mode":"chat"}`，并返回 `{"textResponse":"环保"}` 等合法标签。这是原脚本的服务协议，不是通用 OpenAI API，也不包含知识库构建、检索索引或向量库实现。

```powershell
python -m job_text_classification http --input data/authorized_jobs.jsonl --output outputs/http_predictions.jsonl --timeout 20 --attempts 3 --workers 4
```

请求保留默认 HTTPS 证书校验，使用超时和有界重试；认证等非临时客户端错误直接结束，非法响应只记录错误类型。并发结果保持输入顺序，没有会因失败计数而永久等待的进度线程。失败行照常写出并使 CLI 返回退出码 2；请求体、服务回复正文和凭据不进入输出。

## 公开范围与验证

本工程基于原研究脚本的分类与批处理功能重新组织。原先名为 `bert_classifier.py` 的脚本实际使用 TF-IDF 和随机森林，公开版按真实方法命名；BERT 保留为可选路径。这里的验证针对代码流程，不提供论文效果或个人贡献归属的证明。

- 保留：数据接口、训练与推理代码、HTTP 适配、全新合成例子和回归测试。
- 排除：原始岗位语料、Excel、论文及审稿材料、真实输出、服务地址、密钥、模型与既有实验指标。
- 回归测试覆盖：训练词表隔离、概率列对齐、固定指标标签顺序、重复文本划分限制、模型保存加载、HTTP 超时/非法响应/认证失败、并发保序和输出不带原文。
- 本地验证范围：Python 语法编译、CPU 随机森林合成 demo、模拟 HTTP。没有调用真实服务或运行 BERT 训练。

主要依赖来自 [scikit-learn](https://scikit-learn.org/)、可选 [PyTorch](https://pytorch.org/) 和 [Transformers](https://github.com/huggingface/transformers)。本目录未复制这些依赖的源代码或模型文件；本轮未新增开源许可证。
