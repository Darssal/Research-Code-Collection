# 贡献与维护

本仓库维护项目导航、跨项目设计笔记、来源和公开检查工具。实现、依赖、样例和项目测试的修改应提交到 README 对应的独立仓库；本索引不接受第二份项目源码。

## 提交前

1. 核对链接指向项目当前维护入口；历史链接须明确标注为追溯用途。
2. 明确选择本次改动的文件并暂存，检查 `git diff --cached` 和文件清单。
3. 执行以下检查。报告写到仓库外；默认全目录检查适用于无缓存、无本地环境的干净快照。

```bash
python -B tools/check_index.py
python -B -m unittest discover -s tests -v
python -B tools/check_publication.py
python -B tools/check_publication.py --staged
git diff --cached --check
```

`python -B tools/check_index.py --remote` 另用已安装的 GitHub CLI 只读核对独立仓库的默认分支和链接文件。CI 以只读 token 执行此检查，不需要扩大账号权限。

## 变更说明

Pull Request 写清链接或说明的问题、改后的阅读入口及实际检查结果。模型效果需要对应实验依据，不能把单元测试数量或合成例子的指标写成研究结论。保留外部框架、模型与参考实现来源，不将上游许可证推定为本仓库的统一许可证。
