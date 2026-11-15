#!/usr/bin/env bash
#
# LeetCode 刷题进度自动同步脚本（由 macOS launchd 调用）。
# 职责：检测到 solutions/leetcode/editor/cn/ 变化（或定时）后，
#       1) 拉取远端最新（避免分叉）  2) 重跑分类脚本生成周报
#       3) 若有变更则 git 提交并推送 develop、再同步 main 到 GitHub。
#
set -u
REPO="/Users/wuziyou/Documents/source/github.com/leetcode-solutions"
PY="/usr/local/bin/python3"
LOG="$HOME/Library/Logs/leetcode-autosync.log"
LOCK="$REPO/tools/.autosync.lock"

exec >>"$LOG" 2>&1
echo "===== $(date '+%Y-%m-%d %H:%M:%S') 触发 ====="

# 防重入：用目录锁（macOS 无 flock，mkdir 原子）
# 陈旧锁自愈：若锁目录超过 10 分钟未被清理（上次进程被 launchd 收掉、trap 没跑到），
# 视为僵尸锁直接删除，否则会永久 "上一次同步仍在运行" 卡死同步。
if [ -d "$LOCK" ]; then
  lock_age=$(( $(date +%s) - $(stat -f %m "$LOCK" 2>/dev/null || echo 0) ))
  if [ "$lock_age" -gt 600 ]; then
    rmdir "$LOCK" 2>/dev/null && echo "清理陈旧锁(已存在 ${lock_age}s)"
  fi
fi
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "skip: 上一次同步仍在运行"
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

cd "$REPO" || { echo "cd 失败"; exit 1; }

# 拉取远端最新并变基，避免本地 develop 与远端分叉
git fetch origin >/dev/null 2>&1
git rebase origin/develop >/dev/null 2>&1 || git rebase --abort >/dev/null 2>&1

# 【网页做题同步】作者习惯在 leetcode.cn 网页上做题, 代码只存在 LeetCode 服务器,
# 本地不会生成文件。所以同步前先从网页把新提交的题解拉下来, 再走下面的分类+提交。
# 该脚本自带容错: 登录态失效/钥匙串不可用时只打日志并返回 0, 不阻断本流程。
"$PY" "$REPO/tools/fetch_web_submissions.py" || echo "warn: 网页同步异常(已跳过, 继续本地流程)"

# 重跑分类（生成/更新 WEEKLY_REPORT.md 与 weeks/）
"$PY" "$REPO/tools/classify.py" || { echo "classify 失败"; exit 1; }

# 重建 INDEX.md 总清单（按题号 / 按难度，附分类后的练习日期）
"$PY" "$REPO/tools/build_index.py" || echo "warn: 重建 INDEX 失败(继续本地流程)"

# 有变更才提交 + 推送。
# 先 add -A 再判断暂存区：老写法 git diff --quiet 看不到「只新增了未跟踪文件」的情况，
# 会把新增的题解/脚本漏掉不提交。
git -c core.quotePath=false add -A
if ! git -c core.quotePath=false diff --cached --quiet; then
  git -c core.quotePath=false commit -q -m "chore: 自动同步刷题进度与周报分类"
  git push origin develop || { echo "push develop 失败"; exit 1; }
  git push origin develop:main --force-with-lease || echo "warn: main 同步失败（下次重试）"
  echo "synced OK"
else
  echo "无变更，跳过提交"
fi
echo "----- 完成 -----"
