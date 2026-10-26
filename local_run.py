#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地运行 / 测试 LeetCode 解法的小框架。

用法:
    python3 local_run.py 15              # 跑第 15 题（自动用它的官方用例）
    python3 local_run.py 15 --fetch      # 本地没用例时, 先从 LeetCode 官方拉一份再跑
    python3 local_run.py 9 --list        # 只列出第 9 题的用例, 不执行
    python3 local_run.py 21              # 链表/树类题目自动做结构转换

用例从哪来（按优先级）:
    1. testcases/0015.json —— LeetCode 官方示例用例（tools/fetch_testcases.py 拉取）
    2. 本文件底部的 TESTCASES —— 早期手写的那几道, 作为兜底

它做了什么:
    1. 在 solutions/leetcode/editor/cn/ 里按题号找到 [NNNN]标题.{py,c,cpp}
    2. Python 题(.py): 动态加载 Solution 类, 用官方用例跑并比对官方期望输出
    3. C/C++ 题(.c/.cpp): 调 gcc/g++ 编译, 运行其自带 main() 的 PASS/FAIL 断言
    4. SQL 题(数据库题): 用 PostgreSQL(优先) / SQLite(兜底) 建表、灌官方数据、
       执行你写的 SQL, 再与官方结果表比对（写的 MySQL 方言会自动适配）

说明:
    - 如果某题还是空壳(stub, 方法体没实现), 会提示先填解法。
    - 少数题正文没写期望输出, 这时只执行并打印结果, 不判对错。
"""

import importlib.util
import inspect
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
CN_DIR = os.path.join(ROOT, "solutions", "leetcode", "editor", "cn")
TC_DIR = os.path.join(ROOT, "testcases")


# ---- 链表 / 树 的辅助结构(供需要它们的题目复用) ----
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


def to_listnode(xs):
    head = ListNode(0)
    p = head
    for x in (xs or []):
        p.next = ListNode(x)
        p = p.next
    return head.next


def from_listnode(node):
    """链表转 list。带防环保护 —— 环形链表题返回的就是环上的节点, 不加保护会死循环。"""
    out, seen = [], set()
    while node and id(node) not in seen:
        seen.add(id(node))
        out.append(node.val)
        node = node.next
    return out


def to_treenode(xs):
    """把 LeetCode 层序数组(可含 null) 转成 TreeNode。"""
    if not xs:
        return None
    vals = list(xs)
    root = TreeNode(vals[0])
    queue, i = [root], 1
    while queue and i < len(vals):
        node = queue.pop(0)
        if i < len(vals) and vals[i] is not None:
            node.left = TreeNode(vals[i])
            queue.append(node.left)
        i += 1
        if i < len(vals) and vals[i] is not None:
            node.right = TreeNode(vals[i])
            queue.append(node.right)
        i += 1
    return root


def from_treenode(root):
    """TreeNode 转回层序数组（末尾的 null 去掉）。"""
    if not root:
        return []
    out, queue = [], [root]
    while queue:
        node = queue.pop(0)
        if node is None:
            out.append(None)
            continue
        out.append(node.val)
        queue.append(node.left)
        queue.append(node.right)
    while out and out[-1] is None:
        out.pop()
    return out


# ---- 早期手写的兜底用例 ----
# 格式: 题号 -> (mode, [ (输入参数元组, 期望输出), ... ])
TESTCASES = {
    1: ("plain", [
        (([2, 7, 11, 15], 9), [0, 1]),
        (([3, 2, 4], 6), [1, 2]),
        (([-1, -2, -3, -4], -7), [2, 3]),
    ]),
    9: ("plain", [
        ((121,), True),
        ((123,), False),
        ((10,), False),
    ]),
    2: ("listnode", [
        (([2, 4, 3], [5, 6, 4]), [7, 0, 8]),
        (([0], [0]), [0]),
    ]),
    21: ("listnode", [
        (([1, 2, 4], [1, 3, 4]), [1, 1, 2, 3, 4, 4]),
    ]),
    206: ("listnode", [
        (([1, 2, 3, 4, 5],), [5, 4, 3, 2, 1]),
    ]),
}


def find_file(pid):
    pid = int(pid)
    if not os.path.isdir(CN_DIR):
        return None
    for fn in os.listdir(CN_DIR):
        m = re.match(r"\[0*(\d+)\]", fn)
        if m and int(m.group(1)) == pid:
            return os.path.join(CN_DIR, fn)
    return None


def prelude_symbols():
    """LeetCode 环境默认可用的常用符号。

    很多解法直接就写 deque / Counter / inf 而不 import（在网页上能跑，本地会 NameError），
    这里提前塞进模块命名空间；如果解法自己 import 了，会以它自己的为准。
    """
    import bisect
    import collections
    import functools
    import heapq
    import itertools
    import math
    import typing

    syms = {
        "ListNode": ListNode, "TreeNode": TreeNode,
        "deque": collections.deque, "defaultdict": collections.defaultdict,
        "Counter": collections.Counter, "OrderedDict": collections.OrderedDict,
        "heapq": heapq, "heappush": heapq.heappush, "heappop": heapq.heappop,
        "heapify": heapq.heapify, "nlargest": heapq.nlargest, "nsmallest": heapq.nsmallest,
        "bisect": bisect, "bisect_left": bisect.bisect_left,
        "bisect_right": bisect.bisect_right, "insort": bisect.insort,
        "math": math, "inf": math.inf, "sqrt": math.sqrt,
        "floor": math.floor, "ceil": math.ceil,
        "functools": functools, "reduce": functools.reduce, "lru_cache": functools.lru_cache,
        "itertools": itertools, "collections": collections, "typing": typing,
    }
    for n in ("List", "Dict", "Set", "Tuple", "Optional"):
        syms[n] = getattr(typing, n)
    return syms


def load_solution(path):
    """加载解法文件。优先 Solution；设计类题目(225/232/303 等)会自动找主类。

    找不到任何类时返回 None —— 多半是 SQL 题(文件里是 SQL 语句)或空文件。
    """
    spec = importlib.util.spec_from_file_location("leetcode_sol", path)
    mod = importlib.util.module_from_spec(spec)
    mod.__dict__.update(prelude_symbols())
    spec.loader.exec_module(mod)
    if hasattr(mod, "Solution"):
        return mod.Solution
    # 设计类题目定义的不是 Solution, 而是 MyQueue / MyStack / NumArray 之类
    for name, obj in vars(mod).items():
        if (inspect.isclass(obj) and not name.startswith("_")
                and obj.__module__ == "leetcode_sol"):
            return obj
    return None


def load_official(pid):
    """读 testcases/NNNN.json（官方示例用例）。"""
    path = os.path.join(TC_DIR, "%04d.json" % int(pid))
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def resolve(pid):
    """决定这题用什么用例/模式/方法。返回 (mode, cases, source, method)。"""
    info = load_official(pid)
    if info:
        cases = [(tuple(c.get("input") or []), c.get("output"))
                 for c in (info.get("cases") or [])]
        return (info.get("mode") or "plain", cases,
                "官方用例 testcases/%04d.json" % int(pid),
                info.get("method") or None)
    if int(pid) in TESTCASES:
        mode, cases = TESTCASES[int(pid)]
        return mode, cases, "内置手写用例(兜底)", None
    return None, None, None, None


def to_listnode_with_cycle(xs, pos):
    """LeetCode 环形链表题: pos 表示尾节点接回第 pos 个节点(0 起), -1 表示无环。"""
    head = to_listnode(xs)
    if pos is None or pos < 0 or not xs:
        return head
    nodes, p = [], head
    while p:
        nodes.append(p)
        p = p.next
    if pos < len(nodes):
        nodes[-1].next = nodes[pos]   # 接成环
    return head


# 官方 metaData 里混进来的「构造用参数」: 只用于生成测试数据, 不该传给解法函数
CONSTRUCT_PARAMS = {"pos", "intersectVal", "skipA", "skipB", "pick", "bad"}


def _nodes(xs):
    """数组 -> ListNode 列表(依次相连)。"""
    nodes = [ListNode(x) for x in (xs or [])]
    for i in range(len(nodes) - 1):
        nodes[i].next = nodes[i + 1]
    return nodes


def build_intersect(a_vals, b_vals, skip_a, skip_b):
    """按官方的 skipA/skipB 让两个链表真正相交(共用同一段节点)。"""
    na, nb = _nodes(a_vals), _nodes(b_vals)
    if not na:
        return (None, nb[0] if nb else None)
    if skip_a >= len(na):
        return (na[0], nb[0] if nb else None)
    if skip_b == 0:
        hb = na[skip_a]
    elif nb:
        for i in range(min(skip_b, len(nb)) - 1):
            nb[i].next = nb[i + 1]
        if skip_b - 1 < len(nb):
            nb[skip_b - 1].next = na[skip_a]
        hb = nb[0]
    else:
        hb = None
    return (na[0], hb)


def build_args(mode, args, params=None):
    """把官方用例的输入转成 Python 实参。

    params 是官方 metaData 的参数列表, 用来识别 pos/skipA/bad 这类"构造用参数"——
    它们只参与构造测试数据(环形链表、相交链表、猜数字的答案), 不该被当作函数入参。
    """
    params = params or []
    named, real = {}, list(args)
    if len(params) == len(args):
        for p, a in zip(params, args):
            named[p.get("name")] = a
        real = [a for p, a in zip(params, args)
                if p.get("name") not in CONSTRUCT_PARAMS]

    if mode == "listnode":
        iv, sa, sb = named.get("intersectVal"), named.get("skipA"), named.get("skipB")
        lists = [a for a in real if isinstance(a, list)]
        if iv and sa is not None and sb is not None and len(lists) >= 2:
            ha, hb = build_intersect(lists[0], lists[1], sa, sb)
            return (ha, hb) + tuple(a for a in real if not isinstance(a, list))
        pos_val = named.get("pos")
        out = []
        for a in real:
            if isinstance(a, list):
                out.append(to_listnode_with_cycle(a, pos_val)
                           if pos_val is not None else to_listnode(a))
            else:
                out.append(a)
        return tuple(out)
    if mode == "treenode":
        return tuple(to_treenode(a) if isinstance(a, list) else a for a in real)
    return tuple(real)


def norm(mode, val):
    if mode == "listnode" and isinstance(val, ListNode):
        return from_listnode(val)
    if mode == "treenode" and isinstance(val, TreeNode):
        return from_treenode(val)
    # 空链表 / 空树: 解法一般返回 None, 而官方期望写作 []
    if mode in ("listnode", "treenode") and val is None:
        return []
    return val


def _tree_vals(xs):
    return [x for x in (xs or []) if x is not None]


def _inorder(xs):
    out = []

    def dfs(n):
        if not n:
            return
        dfs(n.left)
        out.append(n.val)
        dfs(n.right)

    dfs(to_treenode(xs))
    return out


def _height(node):
    return 0 if not node else 1 + max(_height(node.left), _height(node.right))


def _balanced(node):
    if not node:
        return True
    if abs(_height(node.left) - _height(node.right)) > 1:
        return False
    return _balanced(node.left) and _balanced(node.right)


def tree_equivalent(got, expected):
    """树结构的答案常常不唯一(如 108 有序数组转二叉搜索树)。

    严格相等比不出来时, 退一步做语义校验:
    节点值集合一致 + 中序遍历有序(说明是合法 BST) + 高度平衡。
    通过返回说明文字, 不通过返回 None。
    """
    if sorted(map(str, _tree_vals(got))) != sorted(map(str, _tree_vals(expected))):
        return None
    io = _inorder(got)
    if io != sorted(io):
        return None
    root = to_treenode(got)
    if root and not _balanced(root):
        return None
    return "值集合一致 / 中序有序(BST) / 高度平衡"


def pick_method(Solution, preferred):
    """优先用官方 metaData 给的方法名, 其次取第一个公开方法。"""
    if preferred and hasattr(Solution, preferred):
        return preferred
    for name in dir(Solution):
        if not name.startswith("_"):
            attr = getattr(Solution, name, None)
            if callable(attr):
                return name
    return None


def run_compiled(path, pid):
    """编译并运行 C(.c)/C++(.cpp) 解法文件, 判定其自带 main() 里的 PASS/FAIL。"""
    ext = os.path.splitext(path)[1].lower()
    compiler = "g++" if ext == ".cpp" else "gcc"
    out = tempfile.mktemp(suffix=".out")
    try:
        build = subprocess.run([compiler, path, "-o", out],
                               capture_output=True, text=True)
        if build.returncode != 0:
            print(f"[!] 编译失败 ({compiler} {os.path.basename(path)}):")
            print(build.stderr)
            return False
        exe = subprocess.run([out], capture_output=True, text=True)
        if exe.stdout:
            print(exe.stdout, end="")
        if exe.stderr:
            print(exe.stderr, end="")
        combined = exe.stdout + exe.stderr
        if exe.returncode != 0 or "FAIL" in combined:
            print(f"[✗] 第 {pid} 题 C/C++ 测试未通过 (exit={exe.returncode})")
            return False
        print(f"[✓] 第 {pid} 题 C/C++ 编译运行通过")
        return True
    finally:
        try:
            os.unlink(out)
        except OSError:
            pass


def run(pid):
    path = find_file(pid)
    if not path:
        print(f"[!] 找不到第 {pid} 题的文件(应在 {CN_DIR})")
        return False
    ext = os.path.splitext(path)[1].lower()
    if ext in (".c", ".cpp"):
        return run_compiled(path, pid)

    mode, cases, source, method = resolve(pid)
    if not cases:
        print(f"[!] 第 {pid} 题还没有用例。")
        print(f"    可以先拉官方的: python3 tools/fetch_testcases.py {pid}")
        print(f"    或者一步到位  : python3 local_run.py {pid} --fetch")
        return False

    info = load_official(pid) or {}
    if mode == "sql":
        return run_sql_problem(pid, path, info)

    print(f"[*] 加载: {os.path.basename(path)}")
    print(f"[*] 用例: {source}（{len(cases)} 组, mode={mode}）")
    params = info.get("params") or []
    ret_void = (info.get("return_type") == "void")
    # 入参和返回值可能是不同形态(如 108 题: 入参是数组、返回是树), 所以模式分开取
    in_mode = info.get("in_mode") or mode
    out_mode = info.get("out_mode") or mode

    try:
        Solution = load_solution(path)
    except Exception as e:
        print(f"[!] 加载失败: {type(e).__name__}: {e}")
        print("    提示: 如果这是 SQL 题, 本框架跑不了, 请用 MySQL 验证。")
        return False
    if Solution is None:
        print("[!] 文件里找不到可运行的类 —— 多半是 SQL 题或空壳（SQL 请用 MySQL 验证）。")
        return False

    fname = pick_method(Solution, method)
    if not fname:
        print("[!] 解法里没有任何方法(可能是空壳)。")
        return False

    if mode == "design":
        return run_design_problem(pid, info, Solution)

    all_ok = True
    for i, (args, expected) in enumerate(cases, 1):
        try:
            inst = Solution()
            # 交互题: 官方运行时会提供 guess(num) / isBadVersion(version),
            # 这里用官方给的 pick / bad 参数模拟出来。
            # 解法多半把它们当全局函数调用, 所以既要挂到实例上, 也要塞进模块全局。
            for pi, p in enumerate(params):   # 用 pi, 免得盖掉外层用例序号 i
                pname = p.get("name")
                if pname in ("pick", "bad") and pi < len(args):
                    secret = args[pi]

                    def _mock(v, _s=secret):
                        if pname == "pick":
                            return -1 if v > _s else (1 if v < _s else 0)
                        return v >= _s

                    setattr(inst, "guess" if pname == "pick" else "isBadVersion", _mock)
                    g = getattr(getattr(Solution, fname, None), "__globals__", None)
                    if isinstance(g, dict):
                        g["guess" if pname == "pick" else "isBadVersion"] = _mock
            fn = getattr(inst, fname)
            # 只传函数真正接受的参数个数: pos/pick 等只是构造测试数据用的, 不该传入
            try:
                sig = inspect.signature(fn)
                n_acc = len([p for p in sig.parameters.values()
                             if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
            except (TypeError, ValueError):
                n_acc = len(args)
            call_args = build_args(in_mode, args, params)[:max(n_acc, 0)]
            ret = fn(*call_args)
            arr = call_args[0] if call_args else None
            if ret_void:
                # 原地修改类题目(如第88题): 答案在被改过的第一个入参里
                got = norm(out_mode, arr)
            else:
                got = norm(out_mode, ret)
        except Exception as e:
            print(f"  用例 {i}: 执行出错 -> {type(e).__name__}: {e}")
            all_ok = False
            continue

        if expected is None:
            print(f"  用例 {i}: ➖ 无官方期望输出, 仅执行 | 输入={args} 得到={got}")
            continue

        # 26/27 这类: 官方期望是 "k, nums = [...]" —— 既看返回值, 也看原地改后的数组
        if isinstance(expected, dict) and "k" in expected:
            k = expected["k"]
            want = expected.get("nums") or []
            head = arr[:k] if isinstance(arr, list) else []
            ok = (got == k) and sorted(map(str, head)) == sorted(map(str, want))
            note = "（返回值 + 原地数组）"
            all_ok = all_ok and ok
            print(f"  用例 {i}: {'✅' if ok else '❌'} 期望 k={k}, nums={want} "
                  f"实际 k={got}, nums={head}{note}")
            continue

        # 相交链表: 官方期望写的是交点的值, 或 "No intersection"
        if isinstance(expected, dict) and "intersect" in expected:
            ok = not got          # 不相交时解法应返回 None / []
            all_ok = all_ok and ok
            print(f"  用例 {i}: {'✅' if ok else '❌'} 期望无交点 实际={got or 'None'}")
            continue

        ok = (got == expected)
        note = ""
        if not ok and isinstance(expected, int) and isinstance(got, list) and got:
            if got[0] == expected:
                ok, note = True, "（交点值一致）"
        # 树结构答案可能不唯一(如 108 有序数组转 BST): 严格不等时做语义校验
        if not ok and out_mode == "treenode" and isinstance(got, list) \
                and isinstance(expected, list):
            why = tree_equivalent(got, expected)
            if why:
                ok, note = True, "（结构不唯一, 已校验: %s）" % why
        if not ok and isinstance(got, list) and isinstance(expected, list):
            # 交集/组合这类题答案顺序无所谓, 排序后一致也算对
            try:
                if sorted(got, key=str) == sorted(expected, key=str):
                    ok, note = True, "（顺序不同, 按集合等价通过）"
            except Exception:
                pass
        all_ok = all_ok and ok
        print(f"  用例 {i}: {'✅' if ok else '❌'} 输入={args} 期望={expected} 实际={got}{note}")

    if all_ok:
        print(f"[✓] 第 {pid} 题全部通过")
    else:
        print(f"[✗] 第 {pid} 题有用例没过(或仍是空壳)")
    return all_ok


def run_design_problem(pid, info, Solution):
    """设计类题目(225 用队列实现栈、303 区域和检索 等):

    官方给的是「操作序列 + 参数序列」, 例如
        ["MyStack","push","top","pop"] / [[],[1],[],[]]
    期望输出是 ["null","null","1","1"]。这里按顺序一步步调用再比对整条序列。
    """
    cases = info.get("cases") or []
    all_ok = True
    for i, case in enumerate(cases, 1):
        inp = case.get("input") or []
        ops = inp[0] if inp else []
        op_args = inp[1] if len(inp) > 1 else []
        expected = case.get("output")
        got, inst = [], None
        try:
            for op, a in zip(ops, op_args or []):
                a = list(a) if isinstance(a, (list, tuple)) else ([a] if a is not None else [])
                if inst is None:
                    inst = Solution(*a)        # 第一个操作就是构造
                    got.append(None)
                    continue
                fn = getattr(inst, op, None)
                if fn is None:
                    print(f"  用例 {i}: [!] 类里找不到方法 {op}")
                    got.append(None)
                    continue
                got.append(fn(*a))
        except Exception as e:
            print(f"  用例 {i}: 执行出错 -> {type(e).__name__}: {e}")
            all_ok = False
            continue

        if expected is None:
            print(f"  用例 {i}: ➖ 无官方期望输出, 仅执行 | 得到={got}")
            continue
        ok = [str(x) for x in got] == [str(x) for x in expected]
        all_ok = all_ok and ok
        if ok:
            print(f"  用例 {i}: ✅ 操作序列 {len(ops)} 步, 输出与官方一致")
        else:
            print(f"  用例 {i}: ❌ 操作={ops}")
            print(f"     期望: {expected}")
            print(f"     实际: {got}")
    if all_ok:
        print(f"[✓] 第 {pid} 题通过（设计类, 已按操作序列执行）")
    else:
        print(f"[✗] 第 {pid} 题结果不符")
    return all_ok


def run_sql_problem(pid, path, info):
    """SQL(数据库)类题目: 用 PostgreSQL(优先)/SQLite(兜底) 真跑一遍并比对官方结果表。"""
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        import sql_runner
    except Exception as e:
        print(f"[!] 加载 SQL 引擎失败: {e}")
        return False

    cases = info.get("cases") or []
    print(f"[*] 加载: {os.path.basename(path)}")
    print(f"[*] 用例: 官方 SQL 用例（{len(cases)} 组, "
          f"引擎={'PostgreSQL' if sql_runner.pg_available() else 'SQLite'}）")

    all_ok = True
    for i, case in enumerate(cases, 1):
        ok, got, used = sql_runner.run_case(pid, path, info, case)
        exp = case.get("output") or {}
        exp_rows = exp.get("rows") if isinstance(exp, dict) else None
        all_ok = all_ok and ok
        if exp_rows is None:
            continue
        if ok:
            print("  用例 %d: ✅ [%s] 结果 %d 行, 与官方一致" % (i, used, len(got or [])))
        else:
            print("  用例 %d: ❌ [%s]" % (i, used))
            print("     期望: %s" % exp_rows)
            print("     实际: %s" % got)
    if all_ok:
        print(f"[✓] 第 {pid} 题通过（SQL 已执行）")
    else:
        print(f"[✗] 第 {pid} 题结果不符")
    return all_ok


def list_cases(pid):
    mode, cases, source, _ = resolve(pid)
    if not cases:
        print(f"[!] 第 {pid} 题还没有用例（试试 python3 local_run.py {pid} --fetch）")
        return
    print(f"第 {pid} 题 (mode={mode}, 来源={source}) 示例:")
    for i, (args, expected) in enumerate(cases, 1):
        print(f"  {i}. 输入={args} -> 期望={expected}")


def fetch_then_run(pid):
    """本地没用例时, 先调抓取脚本拉官方的, 再跑。"""
    script = os.path.join(ROOT, "tools", "fetch_testcases.py")
    if not os.path.exists(script):
        print("[!] 找不到 tools/fetch_testcases.py")
        return False
    subprocess.run([sys.executable, script, str(int(pid))])
    if load_official(pid) is None:
        print(f"[!] 第 {pid} 题仍然没拿到用例")
        return False
    return run(pid)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    pid = sys.argv[1]
    if "--fetch" in sys.argv:
        sys.exit(0 if fetch_then_run(pid) else 1)
    if "--list" in sys.argv:
        list_cases(pid)
    else:
        sys.exit(0 if run(pid) else 1)
