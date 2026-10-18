#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地运行 / 测试 LeetCode 解法的小框架。

用法:
    python local_run.py 1            # 跑第 1 题的示例用例
    python local_run.py 9 --list     # 只列出第 9 题的示例, 不执行
    python local_run.py 21           # 跑链表类题目(自动转 ListNode)

它做了什么:
    1. 在 solutions/leetcode/editor/cn/ 里按题号找到 [NNNN]标题.{py,c,cpp}
    2. Python 题(.py): 动态加载文件里的 Solution 类, 跑 TESTCASES 里的示例
    3. C/C++ 题(.c/.cpp): 调用 gcc/g++ 编译, 运行其自带 main() 的 PASS/FAIL 断言

说明:
    - 如果某题还是空壳(stub, 方法体没实现), 会提示先填解法。
    - SQL 类题目(文件里是 MySQL 语句)无法用本脚本跑, 请用 MySQL 验证。
    - 想加新题的用例, Python 题往下面的 TESTCASES 里照格式加即可;
      C/C++ 题的用例写在各自源文件的 main() 里。
"""

import sys
import os
import re
import importlib.util
import subprocess
import tempfile

CN_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "solutions", "leetcode", "editor", "cn")

# ---- 链表 / 树 的辅助结构(供需要它们的题目复用) ----
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

def to_listnode(xs):
    head = ListNode(0)
    p = head
    for x in xs:
        p.next = ListNode(x)
        p = p.next
    return head.next

def from_listnode(node):
    out = []
    while node:
        out.append(node.val)
        node = node.next
    return out

# ---- 每个题的示例用例 ----
# 格式: 题号 -> (mode, [ (输入参数元组, 期望输出), ... ])
#   mode="plain"    : 参数原样传给 Solution
#   mode="listnode" : 参数里的 list 自动转 ListNode, 返回值再转回 list
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
    for fn in os.listdir(CN_DIR):
        m = re.match(r"\[0*(\d+)\]", fn)
        if m and int(m.group(1)) == pid:
            return os.path.join(CN_DIR, fn)
    return None


def load_solution(path):
    # 给模块注入 ListNode, 避免链表题在加载时找不到定义
    spec = importlib.util.spec_from_file_location("leetcode_sol", path)
    mod = importlib.util.module_from_spec(spec)
    mod.ListNode = ListNode
    spec.loader.exec_module(mod)
    return mod.Solution


def build_args(mode, args):
    if mode == "listnode":
        return tuple(to_listnode(a) if isinstance(a, list) else a for a in args)
    return args


def norm(mode, val):
    if mode == "listnode" and isinstance(val, ListNode):
        return from_listnode(val)
    return val


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
    print(f"[*] 加载: {os.path.basename(path)}")
    try:
        Solution = load_solution(path)
    except Exception as e:
        print(f"[!] 加载失败: {e}")
        return False

    pid_int = int(pid)
    if pid_int not in TESTCASES:
        print("[!] TESTCASES 里还没有这道题的示例, 麻烦往 local_run.py 加一下。")
        return False

    mode, cases = TESTCASES[pid_int]
    method = None
    for name in dir(Solution):
        if not name.startswith("_"):
            method = name
            break
    if not method:
        print("[!] Solution 里没有任何方法(可能是空壳)。")
        return False

    all_ok = True
    for i, (args, expected) in enumerate(cases, 1):
        try:
            inst = Solution()
            fn = getattr(inst, method)
            got = fn(*build_args(mode, args))
            got = norm(mode, got)
        except Exception as e:
            print(f"  用例 {i}: 执行出错 -> {type(e).__name__}: {e}")
            all_ok = False
            continue
        ok = (got == expected)
        all_ok = all_ok and ok
        status = "✅" if ok else "❌"
        print(f"  用例 {i}: {status} 输入={args} 期望={expected} 实际={got}")

    if all_ok:
        print(f"[✓] 第 {pid} 题全部通过")
    else:
        print(f"[✗] 第 {pid} 题有用例没过(或仍是空壳)")
    return all_ok


def list_cases(pid):
    pid_int = int(pid)
    if pid_int not in TESTCASES:
        print(f"[!] TESTCASES 里没有第 {pid} 题")
        return
    mode, cases = TESTCASES[pid_int]
    print(f"第 {pid} 题 (mode={mode}) 示例:")
    for i, (args, expected) in enumerate(cases, 1):
        print(f"  {i}. 输入={args} -> 期望={expected}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)
    pid = sys.argv[1]
    if "--list" in sys.argv:
        list_cases(pid)
    else:
        run(pid)
