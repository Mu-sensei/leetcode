#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重建仓库根目录 INDEX.md（「按题号」+「按难度」两份清单）。

数据来源：
  - 题目与文件名：本地 solutions/leetcode/editor/cn/ 下的真实文件；
  - 难度：LeetCode 公开接口 /api/problems/all/ 的 frontend_question_id → difficulty，
          缓存到 tools/.cache/difficulty_map.json（拉不到时回退旧的 allp.json）；
  - 练习日期：tools/classify.py 按 AC 时间分类后保存的 classify_state.json。

由 tools/auto_sync.sh 在每次分类后自动调用，清单不会再出现「题数过时 / 文件名不补零 /
难度分组不准」这类问题。仅使用 Python 标准库。
"""
import os
import re
import json
import urllib.request
from datetime import date

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CN = os.path.join(REPO, "solutions", "leetcode", "editor", "cn")
CACHE = os.path.join(REPO, "tools", ".cache")
DMAP = os.path.join(CACHE, "difficulty_map.json")
ALLP = os.path.join(CACHE, "allp.json")
STATE = os.path.join(CACHE, "classify_state.json")
OUT = os.path.join(REPO, "INDEX.md")
WD = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
LEVELS = {1: "简单", 2: "中等", 3: "困难"}


def load(path, default):
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def difficulty_map():
    """按前台题号取难度。老缓存 allp.json 用的是内部 question_id，不保证与题号一致。"""
    m = load(DMAP, None)
    if isinstance(m, dict) and m:
        return m
    try:
        req = urllib.request.Request(
            "https://leetcode.cn/api/problems/all/",
            headers={"User-Agent": "Mozilla/5.0", "Referer": "https://leetcode.cn/"})
        with urllib.request.urlopen(req, timeout=20) as r:
            data = json.loads(r.read().decode("utf-8"))
        m = {}
        for it in data.get("stat_status_pairs", []):
            fid = it.get("stat", {}).get("frontend_question_id")
            if fid:
                m[str(fid)] = LEVELS.get(it.get("difficulty", {}).get("level"), "—")
        if m:
            os.makedirs(CACHE, exist_ok=True)
            json.dump(m, open(DMAP, "w"), ensure_ascii=False)
            print("[*] 难度映射已缓存:", len(m), "题")
            return m
    except Exception as e:
        print("[!] 难度接口失败，回退旧缓存:", e)
    return load(ALLP, {})


def main():
    dmap = difficulty_map()
    state = load(STATE, {})

    items = {}
    for fn in os.listdir(CN):
        m = re.match(r"\[0*(\d+)\](.+)\.(py|c|cpp)$", fn)
        if not m:
            continue
        fid = int(m.group(1))
        # 同题若有多语言文件，优先保留 .py
        if fid not in items or fn.endswith(".py"):
            items[fid] = (m.group(2).strip(), fn)

    rows = []
    for fid in sorted(items):
        title, fn = items[fid]
        diff = dmap.get(str(fid), "—")
        raw = (state.get(str(fid)) or {}).get("date", "")
        ds = raw
        if raw:
            try:
                ds = "%s(%s)" % (raw, WD[date.fromisoformat(raw).weekday()])
            except Exception:
                pass
        rows.append((fid, title, diff, fn, ds))

    n = len(rows)
    L = [
        "# LeetCode 题解清单（共 %d 题，已 AC）\n" % n,
        "> 由 `tools/build_index.py` 从本地 `solutions/leetcode/editor/cn/` 的真实文件自动生成。",
        "> 难度取自 LeetCode 公开接口（按前台题号），练习日期取自按 AC 时间的周报分类（`tools/classify.py`）。",
        "> 每次自动同步（`tools/auto_sync.sh`）都会重建本清单，无需手工维护。\n",
        "## 一、按题号排序\n",
        "| 题号 | 标题 | 难度 | 文件 | 练习日期 |",
        "|----:|------|------|------|----------|",
    ]
    for fid, title, diff, fn, ds in rows:
        L.append("| %d | %s | %s | `%s` | %s |" % (fid, title, diff, fn, ds))
    L.append("")

    L.append("## 二、按难度分组\n")
    for level in ("简单", "中等", "困难", "—"):
        group = [r for r in rows if r[2] == level]
        if not group:
            continue
        label = "未标注" if level == "—" else level
        L.append("### %s（%d 题）\n" % (label, len(group)))
        L.append("| 题号 | 标题 | 文件 | 练习日期 |")
        L.append("|----:|------|------|----------|")
        for fid, title, diff, fn, ds in group:
            L.append("| %d | %s | `%s` | %s |" % (fid, title, fn, ds))
        L.append("")

    open(OUT, "w", encoding="utf-8").write("\n".join(L))
    print("[*] INDEX.md 已重建:", n, "题 ->", OUT)


if __name__ == "__main__":
    main()
