# Research Code Collection

用于维护研究项目的代码、配置和最小运行说明。公开版本仅包含经过筛选的源码与新编写的合成示例。

| 项目 | 代码入口 | 当前可验证的范围 |
| --- | --- | --- |
| 成像测井裂缝解释 | [FracLogGPT-Lite](https://github.com/Darssal/FracLogGPT-Lite) | 既有独立仓库：实验阶段编排、推理恢复、视觉对比解码与文本标签评测 |
| 招聘文本分类 | [job-text-classification](projects/job-text-classification/) | TF-IDF + 随机森林基线、可选 BERT 分类、外部聊天服务的批处理适配 |
| 多层记忆实验 | [memlab](projects/memlab/) | 上下文组装、缓存与持久化接口、并发会话实验入口、离线逻辑测试 |

各子项目独立安装，具体依赖、运行命令和验证边界见各自 README。分类服务适配器不包含检索索引或知识库建设；memlab 的完整实验需要另行配置外部服务。

## 从这里开始

1. 阅读对应项目的 README，先运行合成示例或离线测试。
2. 按项目说明配置自己的数据路径和服务环境变量。
3. 将运行输出保留在本地；提交前运行公开边界检查。

```bash
python tools/check_publication.py --help
python -m unittest discover -s tests -v
```

## 维护约定

- 真实语料、测井图像、论文正文与审稿材料、模型权重、检查点、预测结果、日志和本地环境文件不进入仓库。
- 示例数据须为新编写的合成内容。公开示例不能从真实数据中抽样或简单替换姓名得到。
- 凭据从环境变量读取，接口地址由使用者配置；不提交真实密钥和私有服务地址。
- 本仓库重新建立 Git 历史，不导入原实验目录的提交历史。
- 没有附带模型训练成绩或论文性能表。合成示例与单元测试只能验证相应代码行为。

详细规则见 [公开范围](docs/PUBLICATION_SCOPE.md)、[贡献与维护](CONTRIBUTING.md) 和 [第三方来源](THIRD_PARTY.md)。检查器是提交前的辅助检查，新增文件仍需人工检查其来源、内容与公开范围。
