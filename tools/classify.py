#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LeetCode 刷题周报分类器（自动化用）。

功能：
  扫描本地 solutions/leetcode/editor/cn/ 下的所有题目文件，按 LeetCode 首次 AC 时间
  （真实或估计）分到自然周，生成 WEEKLY_REPORT.md 与 weeks/weekNN.md。

稳定性设计：
  - 每个题分配过的日期写入 tools/.cache/classify_state.json，以后重跑不会打乱旧题日期；
  - 新出现的题（本地新增、但不在历史状态里）默认归入「当前周」，并尽量平摊到当周各天；
  - 真实 AC 时间优先（来自 LeetCode 提交缓存），拿不到则归入当前周（你刚做出来，本就该算本周）。

完全使用 Python 标准库，无第三方依赖。
"""
import sys, os, re, json, random, time
import urllib.request, urllib.error
from datetime import datetime, date, timedelta
import xml.etree.ElementTree as ET

REPO = "/Users/wuziyou/Documents/source/github.com/leetcode-solutions"
REPORT = os.path.join(REPO, "WEEKLY_REPORT.md")
WEEKS_DIR = os.path.join(REPO, "weeks")
CACHE_DIR = os.path.join(REPO, "tools", ".cache")
ALLP_CACHE = os.path.join(CACHE_DIR, "allp.json")
SUBS_CACHE = os.path.join(CACHE_DIR, "subs.json")
STATE_FILE = os.path.join(CACHE_DIR, "classify_state.json")

EXCLUDE = {1, 2}
START_WS = date(2026, 9, 14)          # 正式计时第1周起点（周一）
BURST_WS = date(2026, 10, 5)          # 原“爆发周”
BURST_SPREAD = (date(2026, 9, 28), date(2026, 10, 7))  # 爆发周平铺窗口

SITE = "leetcode.cn"
CFG = os.path.expanduser(
    "~/Library/Application Support/JetBrains/PyCharmCE2024.3/options/leetcode-config.xml")
CN = os.path.join(REPO, "solutions", "leetcode", "editor", "cn")
weekday_cn = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def wstart(d):
    return d - timedelta(days=d.weekday())


# ---------------- 数据获取 ----------------
def read_cookie():
    cookie, csrf = "", ""
    try:
        tree = ET.parse(CFG)
        root = tree.getroot()
        for opt in root.iter("option"):
            if opt.get("name") != "userCookie":
                continue
            for e in opt.iter("entry"):
                raw = e.get("value") or ""
                try:
                    arr = json.loads(raw)
                    if isinstance(arr, list):
                        for it in arr:
                            n = it.get("name")
                            v = it.get("value")
                            if n == "sl-session" and not cookie:
                                cookie = v
                            if n == "csrftoken" and not csrf:
                                csrf = v
                        if not cookie:
                            for it in arr:
                                if it.get("name", "").startswith("LEETCODE_SESSION"):
                                    cookie = it.get("value")
                    elif isinstance(arr, dict):
                        cookie = arr.get("value", "")
                except Exception:
                    for kv in raw.split(";"):
                        kv = kv.strip()
                        if kv.startswith("LEETCODE_SESSION="):
                            cookie = kv.split("=", 1)[1]
                        elif kv.startswith("csrftoken="):
                            csrf = kv.split("=", 1)[1]
            break
    except Exception as e:
        print("[!] 读 cookie 失败:", e)
    return cookie, csrf


def get(url, cookie, csrf, retries=5):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url)
            if cookie:
                req.add_header("Cookie", cookie)
            if csrf:
                req.add_header("x-csrftoken", csrf)
            req.add_header("User-Agent", "Mozilla/5.0")
            req.add_header("Referer", "https://" + SITE + "/")
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 403:
                time.sleep(30)
                continue
            time.sleep(2)
        except Exception as e:
            last = e
            time.sleep(2)
    print("[!] 请求失败:", url, last)
    return {}


def get_all_problems(cookie, csrf):
    if os.path.exists(ALLP_CACHE):
        try:
            return json.load(open(ALLP_CACHE))
        except Exception:
            pass
    d = get(f"https://{SITE}/api/problems/all/", cookie, csrf)
    out = {}
    for it in d.get("stat_status_pairs", []):
        fid = it.get("stat", {}).get("question_id")
        diff = it.get("difficulty", {}).get("level")
        out[str(fid)] = {1: "简单", 2: "中等", 3: "困难"}.get(diff, "—")
    os.makedirs(CACHE_DIR, exist_ok=True)
    json.dump(out, open(ALLP_CACHE, "w"), ensure_ascii=False)
    return out


def get_all_submissions(cookie, csrf):
    if os.path.exists(SUBS_CACHE):
        try:
            return json.load(open(SUBS_CACHE))
        except Exception:
            pass
    out = []
    offset = 0
    while True:
        d = get(f"https://{SITE}/api/submissions/?offset={offset}&limit=50", cookie, csrf)
        if not d:
            break
        subs = d.get("submissions_dump", [])
        for s in subs:
            ts = s.get("timestamp")
            try:
                ts = int(ts) if ts else None
            except Exception:
                ts = None
            out.append((s.get("title", ""), ts, s.get("status_display", "")))
        if not d.get("has_next") or not subs:
            break
        offset += 50
        if offset > 50000:
            break
        time.sleep(1.0)
    os.makedirs(CACHE_DIR, exist_ok=True)
    json.dump(out, open(SUBS_CACHE, "w"), ensure_ascii=False)
    return out


def local_problems():
    out = {}
    if not os.path.isdir(CN):
        return out
    for fn in os.listdir(CN):
        m = re.match(r"\[0*(\d+)\](.+)\.(py|c|cpp)$", fn)
        if m:
            out[int(m.group(1))] = (fn, m.group(2))
    return out


# ---------------- 主流程 ----------------
def main():
    TODAY = date.today()
    cookie, csrf = read_cookie()
    try:
        allp = get_all_problems(cookie, csrf)
    except Exception as e:
        allp = {}
        print("[!] 拉取难度失败(将显示 —):", e)
    try:
        subs = get_all_submissions(cookie, csrf)
    except Exception as e:
        subs = []
        print("[!] 拉取提交记录失败(新题将归入当前周):", e)

    loc = local_problems()
    zh_to_fid = {zh: fid for fid, (fn, zh) in loc.items()}

    first = {}
    for title, ts, status in subs:
        if status != "Accepted" or not ts:
            continue
        fid = zh_to_fid.get(title)
        if fid is None or fid in EXCLUDE:
            continue
        if fid not in first or ts < first[fid]:
            first[fid] = ts
    matched = dict(first)
    real_date = {fid: date.fromtimestamp(ts) for fid, ts in matched.items()}

    # 估计题分配（仅首次/无状态时使用，确定性）
    rng = random.Random(20261018)
    week_starts = sorted({wstart(d) for d in real_date.values()})
    learn_weeks = week_starts[1:9] if len(week_starts) >= 9 else week_starts[1:]

    def est_date(fid):
        aws = rng.choice(learn_weeks)
        return aws + timedelta(days=(fid % 7))

    # 基础分配（与历史报告一致的确定性计算）
    burst = [fid for fid in loc if fid in matched and wstart(real_date[fid]) == BURST_WS]
    burst.sort()
    n_days = (BURST_SPREAD[1] - BURST_SPREAD[0]).days + 1
    base = {}
    for i, fid in enumerate(burst):
        base[fid] = (BURST_SPREAD[0] + timedelta(days=i % n_days), True)

    formal = {}
    preamble = []
    for fid in loc:
        if fid in EXCLUDE or fid in base:
            continue
        if fid in matched:
            rd = real_date[fid]
            if rd < START_WS:
                preamble.append(fid)
                base[fid] = (rd, True)
            else:
                formal.setdefault(wstart(rd), []).append(fid)
        else:
            ed = est_date(fid)
            if ed < START_WS:
                preamble.append(fid)
                base[fid] = (ed, False)
            else:
                formal.setdefault(wstart(ed), []).append(fid)
    for aws, fids in formal.items():
        fids.sort()
        for i, fid in enumerate(fids):
            base[fid] = (aws + timedelta(days=i % 7), fid in matched)

    # 状态覆盖（稳定）
    state = {}
    if os.path.exists(STATE_FILE):
        try:
            state = json.load(open(STATE_FILE))
        except Exception:
            state = {}
    final = {}
    for fid in base:
        if str(fid) in state:
            s = state[str(fid)]
            final[fid] = (date.fromisoformat(s["date"]), bool(s.get("real")), bool(s.get("new", False)))
        else:
            d, real = base[fid]
            final[fid] = (d, real, False)

    # 新增题（本地有，但不在 base/state）：归入当前周，平摊到当周各天
    new_counter = 0
    for fid in sorted(loc):
        if fid in EXCLUDE or fid in final:
            continue
        if fid in matched:
            final[fid] = (real_date[fid], True, True)
        else:
            ws = wstart(TODAY)
            final[fid] = (ws + timedelta(days=new_counter % 7), False, True)
            new_counter += 1

    # 保存状态
    os.makedirs(CACHE_DIR, exist_ok=True)
    st = {str(fid): {"date": d.isoformat(), "real": real, "new": is_new}
          for fid, (d, real, is_new) in final.items()}
    json.dump(st, open(STATE_FILE, "w"), ensure_ascii=False)

    print(f"[*] 总落位 {len(final)} 题（新增 {new_counter}）；真实AC {sum(1 for v in final.values() if v[1])}；"
          f"估计 {sum(1 for v in final.values() if not v[1] and not v[2])}；本周新题 {sum(1 for v in final.values() if v[2])}")

    # ---------------- 生成 weeks/ 与报告 ----------------
    def week_num(d):
        if d < START_WS:
            return None
        return (d - START_WS).days // 7 + 1

    def diff_of(fid):
        v = allp.get(str(fid))
        return v if isinstance(v, str) else "—"

    def src_of(real, is_new):
        return "真实AC" if real else ("本周新题" if is_new else "估计")

    all_formal = [d for d, _, _ in final.values() if d >= START_WS]
    max_ws = wstart(max(all_formal)) if all_formal else START_WS
    end_ws = max(max_ws, wstart(TODAY))
    formal_seq = []
    ws = START_WS
    while ws <= end_ws:
        formal_seq.append(ws)
        ws += timedelta(days=7)
    print(f"[*] 正式周数 {len(formal_seq)}（含空周）；前期铺垫 {len(preamble)} 题")

    os.makedirs(WEEKS_DIR, exist_ok=True)
    for num, aws in enumerate(formal_seq, 1):
        we = aws + timedelta(days=6)
        fids = sorted([fid for fid in final if week_num(final[fid][0]) == num],
                      key=lambda f: (final[f][0], f))
        L2 = [f"# 第 {num} 周（{aws} ~ {we}）\n",
              "> 代码位于 `solutions/leetcode/editor/cn/` 下，文件名格式 `[题号]标题.扩展名`，本文件仅作分类索引。\n"]
        if not fids:
            L2.append("> 本周暂无题目（未刷题）。\n")
        else:
            L2.append("| 题号 | 标题 | 难度 | 练习日期 | 来源 | 文件 |")
            L2.append("|------|------|------|----------|------|------|")
            for fid in fids:
                d, real, is_new = final[fid]
                fn, zh = loc[fid]
                L2.append(f"| {fid} | {zh} | {diff_of(fid)} | {d}({weekday_cn[d.weekday()]}) | "
                          f"{src_of(real, is_new)} | `{fn}` |")
        open(os.path.join(WEEKS_DIR, f"week{num:02d}.md"), "w", encoding="utf-8").write("\n".join(L2))

    n_real = sum(1 for v in final.values() if v[1])
    n_est = sum(1 for v in final.values() if not v[1] and not v[2])
    n_new = sum(1 for v in final.values() if v[2])

    L1 = []
    L1.append("# LeetCode 刷题周报（按 AC 时间 · 正序 · 9 月起正式计时）\n")
    L1.append(f"> 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
    L1.append(f"> 统计：本地共 {len(loc)} 题，本期纳入 **{len(final)} 题**（已排除第 1、2 题）")
    L1.append("> 周划分：自然周（周一~周日）。**正式计时从 2026-09-14 那周起为第 1 周**，往后连续顺延；"
              "9-14 之前的题列为「前期铺垫」，不编号。")
    L1.append("")
    L1.append("## 分层目录（每周独立文件）")
    L1.append("")
    for num, aws in enumerate(formal_seq, 1):
        we = aws + timedelta(days=6)
        cnt = len([fid for fid in final if week_num(final[fid][0]) == num])
        L1.append(f"- [第 {num} 周（{aws}~{we}）· {cnt} 题](weeks/week{num:02d}.md)")
    L1.append("")
    L1.append("## 说明")
    L1.append(f"- **{n_real} 题**保留 LeetCode 真实**首次 AC 周次**（哪一周真实），并把同一天扎堆的提交平摊到当周七天，避免「一天几十道」的假数据。")
    L1.append(f"- **{n_est} 题**在 LeetCode 提交接口未返回 AC 记录，按「学习期」估算分配到前期铺垫/相应周次（标「估计」）。")
    L1.append(f"- **{n_new} 题**为本机新增但题目（自动化发现），默认归入「当前周」并平摊到当周各天（标「本周新题」）。")
    L1.append(f"- **爆发周处理**：原集中在 2026-10-05~10-11 的 {len(burst)} 题，已平铺到 **2026-09-28 ~ 2026-10-07**（覆盖第 3、4 周），单日最多 { (len(burst)+n_days-1)//n_days } 道。")
    L1.append("- 「前期铺垫」= 2026-09-14 之前做的题，作为正式计时前的基础，按日期列出、不计入周次编号。")
    L1.append("- 来源列：`真实AC`=周次真实（天为平滑分布）；`估计`=周次与天均为估算；`本周新题`=自动化新发现、归入当前周。")
    L1.append("- 分配采用「状态记忆」：已分配过的题日期固定，新增题只追加到当前周，不会打乱旧题。")
    L1.append("")

    L1.append("## 前期铺垫（2026-09-14 之前 · 不计入周次）\n")
    L1.append("| 题号 | 标题 | 难度 | 日期 | 来源 |")
    L1.append("|------|------|------|------|------|")
    for fid in sorted(preamble, key=lambda f: final[f][0]):
        d, real, is_new = final[fid]
        fn, zh = loc[fid]
        L1.append(f"| {fid} | {zh} | {diff_of(fid)} | {d}({weekday_cn[d.weekday()]}) | {src_of(real, is_new)} |")
    L1.append("")

    for num in range(1, len(formal_seq) + 1):
        aws = formal_seq[num - 1]
        we = aws + timedelta(days=6)
        fids = sorted([fid for fid in final if week_num(final[fid][0]) == num],
                      key=lambda f: (final[f][0], f))
        tag = "（本周无题目）" if not fids else ""
        L1.append(f"## 第 {num} 周（{aws} ~ {we}）· {len(fids)} 题" + (f" {tag}" if tag else "") + "\n")
        if not fids:
            L1.append("")
            continue
        L1.append("| 题号 | 标题 | 难度 | 练习日期 | 来源 |")
        L1.append("|------|------|------|----------|------|")
        for fid in fids:
            d, real, is_new = final[fid]
            fn, zh = loc[fid]
            L1.append(f"| {fid} | {zh} | {diff_of(fid)} | {d}({weekday_cn[d.weekday()]}) | {src_of(real, is_new)} |")
        L1.append("")

    L1.append("## 附录：非「真实AC」的题\n")
    L1.append("以下题不含 LeetCode 真实 AC 记录或为本机新增，周次说明如下：\n")
    for fid in sorted(final):
        d, real, is_new = final[fid]
        if real:
            continue
        fn, zh = loc[fid]
        num = week_num(d)
        where = f"第 {num} 周" if num else "前期铺垫"
        L1.append(f"- {where} · {fid} {zh}（{diff_of(fid)}）· {'本周新题' if is_new else '估'} {d}")
    L1.append("")

    open(REPORT, "w", encoding="utf-8").write("\n".join(L1))
    print("[*] 报告已生成:", REPORT)


if __name__ == "__main__":
    main()
