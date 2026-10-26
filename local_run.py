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

说明:
    - 如果某题还是空壳(stub, 方法体没实现), 会提示先填解法。
    - SQL 类题目(文件里是 MySQL 语句)无法用本脚本跑, 请用 MySQL 验证。
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
    out = []
    while node:
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


def load_solution(path):
    """加载解法文件。优先 Solution；设计类题目(225/232/303 等)会自动找主类。

    找不到任何类时返回 None —— 多半是 SQL 题(文件里是 SQL 语句)或空文件。
    """
    spec = importlib.util.spec_from_file_location("leetcode_sol", path)
    mod = importlib.util.module_from_spec(spec)
    mod.ListNode = ListNode
    mod.TreeNode = TreeNode
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


def build_args(mode, args, params=None):
    """把官方用例的输入转成 Python 实参。

    params 是官方 metaData 的参数列表, 用来识别 pos 这类"构造用参数"——
    它只参与构造测试数据(环形链表), 不该被当作函数入参。
    """
    params = params or []
    pos_val = None
    for i, p in enumerate(params):
        if p.get("name") == "pos" and i < len(args):
            pos_val = args[i]
            break

    if mode == "listnode":
        out = []
        for i, a in enumerate(args):
            if isinstance(a, list):
                out.append(to_listnode_with_cycle(a, pos_val)
                           if (i == 0 and pos_val is not None) else to_listnode(a))
            else:
                out.append(a)
        return tuple(out)
    if mode == "treenode":
        return tuple(to_treenode(a) if isinstance(a, list) else a for a in args)
    return args


def norm(mode, val):
    if mode == "listnode" and isinstance(val, ListNode):
        return from_listnode(val)
    if mode == "treenode" and isinstance(val, TreeNode):
        return from_treenode(val)
    # 空链表 / 空树: 解法一般返回 None, 而官方期望写作 []
    if mode in ("listnode", "treenode") and val is None:
        return []
    return val


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

    print(f"[*] 加载: {os.path.basename(path)}")
    print(f"[*] 用例: {source}（{len(cases)} 组, mode={mode}）")
    info = load_official(pid) or {}
    params = info.get("params") or []
    ret_void = (info.get("return_type") == "void")

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

    all_ok = True
    for i, (args, expected) in enumerate(cases, 1):
        try:
            inst = Solution()
            # 交互题(如第374题): 官方运行时提供 guess(num), 这里用 pick 模拟。
            # 解法是把它当全局函数调用的, 所以既要挂到实例上, 也要塞进模块全局。
            for pi, p in enumerate(params):   # 用 pi, 免得盖掉外层用例序号 i
                if p.get("name") == "pick" and pi < len(args):
                    pick = args[pi]

                    def _guess(num, _p=pick):
                        return -1 if num > _p else (1 if num < _p else 0)

                    inst.guess = _guess
                    g = getattr(getattr(Solution, fname, None), "__globals__", None)
                    if isinstance(g, dict):
                        g["guess"] = _guess
            fn = getattr(inst, fname)
            # 只传函数真正接受的参数个数: pos/pick 等只是构造测试数据用的, 不该传入
            try:
                sig = inspect.signature(fn)
                n_acc = len([p for p in sig.parameters.values()
                             if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)])
            except (TypeError, ValueError):
                n_acc = len(args)
            call_args = build_args(mode, args, params)[:max(n_acc, 0)]
            got = fn(*call_args)
            if ret_void:
                # 原地修改类题目(如第88题): 答案在被改过的第一个入参里
                got = norm(mode, call_args[0] if call_args else None)
            else:
                got = norm(mode, got)
        except Exception as e:
            print(f"  用例 {i}: 执行出错 -> {type(e).__name__}: {e}")
            all_ok = False
            continue

        if expected is None:
            print(f"  用例 {i}: ➖ 无官方期望输出, 仅执行 | 输入={args} 得到={got}")
            continue

        ok = (got == expected)
        note = ""
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
