#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从 LeetCode 官方拉取题目的「示例用例」，存为 testcases/NNNN.json。

用法:
    python3 tools/fetch_testcases.py 1 2 9          # 拉指定题号
    python3 tools/fetch_testcases.py --all          # 拉本仓库已有的全部题
    python3 tools/fetch_testcases.py --all --force  # 已存在的也重新拉

数据来源（LeetCode 官方公开接口，无需登录）:
    /api/problems/all/          题号 -> titleSlug
    /graphql/ questionData      exampleTestcases(官方示例输入)
                                metaData(参数名/类型, 用来把输入切成一组组)
                                content(正文, 内含官方示例输出, 用来判定对错)
"""

import ast
import html
import json
import os
import re
import sys
import time
import urllib.request

BASE = "https://leetcode.cn"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, "testcases")
CACHE_DIR = os.path.join(ROOT, "tools", ".cache")
CN_DIR = os.path.join(ROOT, "solutions", "leetcode", "editor", "cn")

GRAPHQL_QUERY = """query questionData($titleSlug: String!) {
  question(titleSlug: $titleSlug) {
    questionFrontendId
    title
    translatedTitle
    content
    exampleTestcases
    metaData
  }
}"""


def _post(url, payload, timeout=25):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={
        "User-Agent": UA,
        "Content-Type": "application/json",
        "Referer": BASE + "/",
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": BASE + "/"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_slug_map(refresh=False):
    """题号 -> slug。缓存到本地，避免每次全量拉取 4483 道题。"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_file = os.path.join(CACHE_DIR, "slug_map.json")
    if os.path.exists(cache_file) and not refresh:
        with open(cache_file, encoding="utf-8") as f:
            return {int(k): v for k, v in json.load(f).items()}
    print("[*] 拉取 题号->slug 映射（仅一次，随后缓存）...")
    data = _get(BASE + "/api/problems/all/")
    mapping = {}
    for item in data.get("stat_status_pairs", []) or []:
        st = item.get("stat", {}) or {}
        fid = str(st.get("frontend_question_id") or "")
        slug = st.get("question__title_slug")
        if fid.isdigit() and slug:
            mapping[int(fid)] = slug
    with open(cache_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f)
    print(f"    拿到 {len(mapping)} 道题的映射\n")
    return mapping


def strip_html(raw):
    """去掉 HTML 标签，把正文变成一行行可读文本（示例会变成 Input:/Output:）。"""
    if not raw:
        return ""
    s = re.sub(r"<br\s*/?>", "\n", raw, flags=re.I)
    s = re.sub(r"</p\s*>", "\n", s, flags=re.I)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s).replace("\xa0", " ")
    return s


def parse_expected_outputs(content):
    """从正文抓官方示例的期望输出。

    兼容 LeetCode 两种正文排版:
      1) <pre>Input: ...\nOutput: [7,0,8]</pre>
      2) <p><strong>Input:</strong> <code>...</code></p>
         <p><strong>Output:</strong> <code>[0,1]</code></p>
    """
    txt = strip_html(content)
    lines = txt.split("\n")
    outs = []
    for idx, ln in enumerate(lines):
        # 注意: 设计类题正文里是 "Output" 后直接换行给值, 没有冒号
        m = re.match(r"\s*(?:Output|输出)\s*[：:]?\s*(.*)$", ln)
        if not m:
            continue
        val = m.group(1).strip()
        if not val:
            # 有些题 Output: 后面换行才给值(设计类题尤其常见)
            k = idx + 1
            while k < len(lines):
                s = lines[k].strip()
                if s:
                    if re.match(r"(解释|Explanation|输入|Input|提示|注意|Note)", s):
                        break
                    val = s
                    break
                k += 1
        # 同一行若还跟着 Explanation/解释，截掉
        val = re.split(r"\s{2,}|Explanation|解释", val)[0].strip()
        if val:
            outs.append(val)
    return outs


def _sql_cell(v):
    """表格单元格 -> Python 值。SQL 的 NULL 转 None, 数字转 int/float, 其余留字符串。"""
    s = "" if v is None else str(v).strip()
    if s.lower() in ("null", "none", ""):
        return None
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    return s


def parse_sql_tables(content):
    """SQL 题专用: 官方输出是一张 ASCII 表格, 解析成 {"columns": [...], "rows": [[...]]}。

    正文形如:
        Output:
        +-----------+----------+
        | firstName | lastName |
        +-----------+----------+
        | Allen     | Wang     |
        +-----------+----------+
    表格里第一个 |...| 行是列名, 其余是数据行。
    """
    txt = strip_html(content)
    lines = txt.split("\n")
    tables = []
    i = 0
    while i < len(lines):
        if not re.match(r"\s*(?:Output|输出)\s*[：:]", lines[i]):
            i += 1
            continue
        # 从 Output 之后开始找表格顶边（遇到下一节标题就放弃）
        j = i + 1
        while j < len(lines) and not lines[j].strip().startswith("+"):
            s = lines[j].strip()
            if s and re.match(r"(解释|Explanation|示例|Example|提示|Constraints)", s):
                break
            j += 1
        if j >= len(lines) or not lines[j].strip().startswith("+"):
            i += 1
            continue
        bar_rows = []
        k = j
        while k < len(lines):
            ln = lines[k].strip()
            if ln.startswith("|"):
                bar_rows.append([c.strip() for c in ln.strip("|").split("|")])
            elif ln.startswith("+"):
                pass
            else:
                break
            k += 1
        if len(bar_rows) >= 2:  # 至少要有列名 + 一行数据
            tables.append({
                "columns": bar_rows[0],
                "rows": [[_sql_cell(c) for c in r] for r in bar_rows[1:]],
            })
        i = max(k, i + 1)
    return tables


def looks_like_ops(example):
    """设计类题目(225/232/303 等): 官方给的是「操作序列 + 参数序列」两行。"""
    lines = [l for l in (example or "").split("\n") if l.strip()]
    # 第一行是操作名数组, 第二行必须是「参数数组的数组」(如 [[],[1],[2]])
    # —— 只凭第一行判断会把 500(键盘行) 这类字符串数组题误判成设计类
    return (len(lines) >= 2 and lines[0].strip().startswith('["')
            and lines[1].strip().startswith("[["))


def normalize_expected(val):
    """把官方输出文本规整成可比对的值。

    - "2, nums = [1,2,_]"          -> {"k": 2, "nums": [1, 2]}   (26/27 这类原地删除题)
    - "Intersected at '8'"         -> 8                          (160 相交链表)
    - "[null,null,null,2,2,false]" -> [None, None, None, 2, 2, False]
    """
    if not isinstance(val, str):
        return val
    s = val.strip()
    m = re.match(r"^(\d+)\s*,\s*nums\s*=\s*(\[.*\])$", s)
    if m:
        nums = parse_literal(re.sub(r"\b_\b", "null", m.group(2)))
        k = int(m.group(1))
        return {"k": k, "nums": list(nums or [])[:k]}
    m = re.match(r"^Intersected at\s*'?(\d+)'?", s)
    if m:
        return int(m.group(1))
    if s.lower().startswith("no intersection"):
        return {"intersect": None}      # 官方表示两个链表不相交
    return parse_literal(s)


def is_sql_question(meta):
    """SQL 题: 没有 params, 但 metaData 里带各数据库的建表语句。"""
    return (not meta.get("params")) and bool(meta.get("mysql"))


def parse_literal(text):
    """把 '[2,7,11,15]' / '9' / 'true' / '"abc"' 这类字面量转成 Python 值。"""
    s = (text or "").strip()
    if not s:
        return None
    # JSON 里的 true/false/null 在 Python 里是 True/False/None
    py = re.sub(r"\btrue\b", "True", s)
    py = re.sub(r"\bfalse\b", "False", py)
    py = re.sub(r"\bnull\b", "None", py)
    for loader in (json.loads, ast.literal_eval):
        try:
            return loader(s)
        except Exception:
            pass
    try:
        return ast.literal_eval(py)
    except Exception:
        return s


def mode_of(type_str):
    """参数/返回值的类型 -> 是否需要结构转换。"""
    t = type_str or ""
    if "TreeNode" in t:
        return "treenode"
    if "ListNode" in t:
        return "listnode"
    return "plain"


def in_mode(meta):
    """入参模式: 任一参数是链表/树, 就需要把数组转成结构。"""
    for p in meta.get("params") or []:
        m = mode_of(p.get("type"))
        if m != "plain":
            return m
    return "plain"


def out_mode(meta):
    """返回值模式: 决定返回值要不要转回数组。"""
    return mode_of((meta.get("return") or {}).get("type"))


def split_cases(example_testcases, n_params):
    """官方示例输入是一整段文本，按参数个数切成一组组用例。"""
    lines = [ln for ln in (example_testcases or "").split("\n") if ln.strip()]
    cases = []
    usable = (len(lines) // n_params) * n_params
    for i in range(0, usable, n_params):
        cases.append([parse_literal(x) for x in lines[i:i + n_params]])
    return cases


def guess_mode(meta):
    """按参数/返回值类型判断是否需要链表或树的结构转换。"""
    blob = json.dumps(meta, ensure_ascii=False)
    if "TreeNode" in blob:
        return "treenode"
    if "ListNode" in blob:
        return "listnode"
    return "plain"


def fetch_one(pid, slug):
    payload = {"operationName": "questionData",
               "variables": {"titleSlug": slug},
               "query": GRAPHQL_QUERY}
    data = _post(BASE + "/graphql/", payload)
    q = (data.get("data") or {}).get("question")
    if not q:
        raise RuntimeError("接口未返回题目数据")

    try:
        meta = json.loads(q.get("metaData") or "{}")
    except Exception:
        meta = {}
    params = meta.get("params") or []
    n_params = max(len(params), 1)

    example = q.get("exampleTestcases")
    content = q.get("content")
    sql_mode = is_sql_question(meta)
    design = (not sql_mode) and looks_like_ops(example)

    if sql_mode:
        # SQL 题: 官方直接给了建表语句和整张数据表, 期望输出是一张结果表
        try:
            data_in = json.loads(example or "")
            if not isinstance(data_in, dict):
                data_in = None
        except Exception:
            data_in = None
        inputs = [[data_in]] if data_in else split_cases(example, 1)
        outputs = parse_sql_tables(content)
    elif design:
        # 设计类题: 官方给「操作序列」+「参数序列」两行, 作为一整组用例
        lines = [l for l in (example or "").split("\n") if l.strip()]
        inputs = [[parse_literal(l) for l in lines]]
        outputs = [normalize_expected(o) for o in parse_expected_outputs(content)]
    else:
        inputs = split_cases(example, n_params)
        outputs = [normalize_expected(o) for o in parse_expected_outputs(content)]

    cases = []
    for i, args in enumerate(inputs):
        cases.append({"input": args, "output": outputs[i] if i < len(outputs) else None})

    info = {
        "pid": int(pid),
        "slug": slug,
        "title": q.get("translatedTitle") or q.get("title") or "",
        "method": meta.get("name") or "",
        "mode": "sql" if sql_mode else ("design" if design else in_mode(meta)),
        # 入参/返回值可能一个是数组一个是结构, 所以模式分开存(如 108 入参数组、返回树)
        "in_mode": "plain" if (sql_mode or design) else in_mode(meta),
        "out_mode": out_mode(meta),
        "params": [{"name": p.get("name"), "type": p.get("type")} for p in params],
        "return_type": (meta.get("return") or {}).get("type"),
        "cases": cases,
    }
    if sql_mode:
        info["ddl"] = meta.get("mysql") or []   # 官方建表语句, 本地建库时直接用
    return info


def repo_pids():
    """扫描 solutions 目录里已有的题号。"""
    pids = set()
    if not os.path.isdir(CN_DIR):
        return []
    for fn in os.listdir(CN_DIR):
        m = re.match(r"\[0*(\d+)\]", fn)
        if m:
            pids.add(int(m.group(1)))
    return sorted(pids)


def main():
    argv = sys.argv[1:]
    force = "--force" in argv
    want_all = "--all" in argv
    pos = [a for a in argv if a.isdigit()]

    if want_all or not pos:
        pids = repo_pids()
        if not pids:
            print("[!] 没在 solutions 目录里找到题目文件")
            return 1
        print(f"[*] 准备处理本仓库 {len(pids)} 道题\n")
    else:
        pids = [int(a) for a in pos]

    slug_map = load_slug_map()
    os.makedirs(OUT_DIR, exist_ok=True)

    ok, fail, no_out, skipped = [], [], [], 0
    for pid in pids:
        out_file = os.path.join(OUT_DIR, "%04d.json" % pid)
        if os.path.exists(out_file) and not force:
            skipped += 1
            continue
        slug = slug_map.get(pid)
        if not slug:
            fail.append((pid, "官方题库里查不到该题号"))
            continue
        try:
            info = fetch_one(pid, slug)
        except Exception as e:
            fail.append((pid, "%s: %s" % (type(e).__name__, str(e)[:60])))
            continue

        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(info, f, ensure_ascii=False, indent=2)

        n_case = len(info["cases"])
        has_out = any(c["output"] is not None for c in info["cases"])
        ok.append(pid)
        if not has_out:
            no_out.append(pid)
        print("  [%4d] %-24s 用例 %d 组  mode=%-8s 期望输出=%s"
              % (pid, info["title"][:24], n_case, info["mode"], "有" if has_out else "无"))
        time.sleep(0.35)

    print("\n===== 汇总 =====")
    print("成功写入 : %d" % len(ok))
    print("跳过(已有): %d" % skipped)
    print("失败     : %d" % len(fail))
    if fail:
        for pid, why in fail[:10]:
            print("   - 第%d题: %s" % (pid, why))
    print("无期望输出(只能跑通、不能判对错): %d" % len(no_out))
    if no_out:
        print("  题号:", ", ".join(str(p) for p in no_out[:30]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
