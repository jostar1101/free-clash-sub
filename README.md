# free-clash-sub

免费代理节点自动聚合订阅。每 6 小时由 GitHub Actions 自动运行 `build.py`，从以下源聚合节点并生成 Clash 配置：

- [Pawdroid/Free-servers](https://github.com/Pawdroid/Free-servers)（18.4k★，6小时更新）
- [xiaoji235/airport-free](https://github.com/xiaoji235/airport-free)（yoyapai 聚合源）
- [zhuhaiuk/free-nodes](https://github.com/zhuhaiuk/free-nodes)（每小时更新）

## Clash 订阅链接

```
https://raw.githubusercontent.com/jostar1101/free-clash-sub/main/clash-merged-clean.yaml
```

在 Clash Verge 中：订阅 → 添加该链接 → 更新。之后每次点更新即可自动获取最新节点。

## 手动触发更新

GitHub 仓库 → Actions → Build Nodes → Run workflow。

## 本地运行

```bash
pip install pyyaml
python build.py
```
