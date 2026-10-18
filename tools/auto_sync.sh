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
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "skip: 上一次同步仍在运行"
  exit 0
fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

cd "$REPO" || { echo "cd 失败"; exit 1; }

# 拉取远端最新并变基，避免本地 develop 与远端分叉
git fetch origin >/dev/null 2>&1
git rebase origin/develop >/dev/null 2>&1 || git rebase --abort >/dev/null 2>&1

# 重跑分类（生成/更新 WEEKLY_REPORT.md 与 weeks/）
"$PY" "$REPO/tools/classify.py" || { echo "classify 失败"; exit 1; }

# 有变更才提交 + 推送
if ! git -c core.quotePath=false diff --quiet; then
  git -c core.quotePath=false add -A
  git -c core.quotePath=false commit -q -m "chore: 自动同步刷题进度与周报分类"
  git push origin develop || { echo "push develop 失败"; exit 1; }
  git push origin develop:main --force-with-lease || echo "warn: main 同步失败（下次重试）"
  echo "synced OK"
else
  echo "无变更，跳过提交"
fi
echo "----- 完成 -----"
