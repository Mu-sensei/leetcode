class Solution(object):
    def generateParenthesis(self, n):
        """
        :type n: int
        :rtype: List[str]

        解法二 · 栈版（迭代回溯）：用显式栈模拟递归回溯，不使用函数递归。
        思路：栈里每个元素是一个状态 (left, right, current)，
        left/right 是已用的左/右括号个数，current 是当前拼出的串。
        弹出一个状态：若左右都用满就收进结果；
        否则按两条规则继续压栈——左括号没用完就能加 '('，
        右括号数量小于左括号时才能加 ')'（保证任何前缀都合法）。
        """
        result = []
        stack = [(0, 0, "")]
        while stack:
            left, right, current = stack.pop()
            if left == n and right == n:
                result.append(current)
                continue
            # 先压 ')' 再压 '('，栈是后进先出，弹出时 '(' 优先，顺序与递归版一致
            if right < left:
                stack.append((left, right + 1, current + ')'))
            if left < n:
                stack.append((left + 1, right, current + '('))
        return result
