# LeetCode 刷题进度 · 自动同步说明

做完题 → 自动分类到周 → 自动推到 GitHub，全程不用手动干预。

## 自动链路

```
你在 PyCharm(leetcode-editor 插件) 提交一题
   或在 LeetCode 网页做完 + 插件自动同步
        │  本地 solutions/leetcode/editor/cn/ 出现/更新文件
        ▼
macOS launchd 监控到变化（每 10 分钟也会兜底轮询）
        ▼
tools/auto_sync.sh
   1. git fetch + rebase（避免分叉）
   2. tools/classify.py 重新分类生成 WEEKLY_REPORT.md + weeks/weekNN.md
   3. 有变更则 git commit → push develop → 同步 main
        ▼
GitHub 仓库自动更新（默认分支 main 即最新）
```

## 你平时要做的

- **在 PyCharm 里用 leetcode-editor 插件做题/提交**：插件会把代码写到本地 `solutions/...`，自动同步脚本接管后面的事。
- **在 LeetCode 网页做题**：只要 PyCharm 里插件开着「自动同步」（插件设置里开启），网页做的题会被拉到本地，同样自动入库。
  - 若不想开插件自动同步，也可以手动在插件里点一下「Sync」再关掉，脚本会在 10 分钟内兜底处理。

做完题后最多等 **10 分钟**（或目录一变化立即），GitHub 上就能看到新题和更新的周报。

## 分类规则（自动）

- 题按 LeetCode **首次 AC 真实时间**分到自然周；9-14 之前归「前期铺垫」（不编号）。
- 同一天扎堆的提交会被平摊到当周各天（不会出现“一天 24 道”）。
- **新做的题**：脚本发现本地多出的文件，默认归入「当前周」并平摊，不打乱旧题日期（状态记忆在 `tools/.cache/classify_state.json`）。

## 文件清单

| 文件 | 作用 |
|------|------|
| `tools/classify.py` | 分类器：扫描本地题 → 生成周报 + weeks/ 分层文件（纯标准库） |
| `tools/auto_sync.sh` | 同步器：拉取/分类/提交/推送（含防重入锁） |
| `~/Library/LaunchAgents/com.leetcode.autosync.plist` | launchd 配置：监控目录 + 10 分钟轮询 |
| `tools/.cache/` | 缓存（LeetCode 题难度/提交记录 + 分类状态），已 gitignore |
| `~/Library/Logs/leetcode-autosync.log` | 运行日志 |

## 管理命令

```bash
# 查看运行状态 / 日志
cat ~/Library/Logs/leetcode-autosync.log

# 立即手动跑一次（等效自动化）
bash ~/Documents/source/github.com/leetcode-solutions/tools/auto_sync.sh

# 暂停自动化
launchctl unload ~/Library/LaunchAgents/com.leetcode.autosync.plist

# 恢复自动化
launchctl load ~/Library/LaunchAgents/com.leetcode.autosync.plist

# 卸载（彻底移除）
launchctl unload ~/Library/LaunchAgents/com.leetcode.autosync.plist
rm ~/Library/LaunchAgents/com.leetcode.autosync.plist
```

## 备注 / 故障排查

- 首次 `git push` 可能弹一次钥匙串授权（允许“访问 github.com”即可），之后记住，不再弹。
- 若 LeetCode 登录态过期，新题仍会被归入「当前周」（日期正确）；想拿真实 AC 周次，重新登录插件后脚本下次运行会自动刷新缓存。
- 若某次自动提交发生冲突，脚本会跳过本次提交并在日志写明，下次重试；一般不会冲突（solo 仓库、仅此脚本写 develop）。
