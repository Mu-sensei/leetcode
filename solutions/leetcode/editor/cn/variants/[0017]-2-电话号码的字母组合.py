class Solution(object):
    def letterCombinations(self, digits):
        """
        :type digits: str
        :rtype: List[str]

        解法二 · 栈版（迭代回溯）：用显式栈模拟递归回溯，不使用函数递归。
        思路：栈里每个元素是一个「状态」(index, current)，
        index 表示当前处理到第几位数字，current 是已经拼出的字母串。
        弹出一个状态：若已拼完（index == len(digits)）就收进结果；
        否则把这一位数字对应的所有字母各拼一个状态压回栈里，继续处理下一位。
        """
        if not digits:
            return []
        digit_to_letters = {
            '2': 'abc',
            '3': 'def',
            '4': 'ghi',
            '5': 'jkl',
            '6': 'mno',
            '7': 'pqrs',
            '8': 'tuv',
            '9': 'wxyz'
        }
        result = []
        stack = [(0, "")]
        while stack:
            index, current = stack.pop()
            if index == len(digits):
                result.append(current)
                continue
            # 反着压栈，弹出时顺序与递归版一致（a→b→c）
            for letter in reversed(digit_to_letters[digits[index]]):
                stack.append((index + 1, current + letter))
        return result
