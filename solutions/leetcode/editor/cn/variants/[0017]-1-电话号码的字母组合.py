class Solution(object):
    def letterCombinations(self, digits):
        """
        :type digits: str
        :rtype: List[str]
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
            for letter in reversed(digit_to_letters[digits[index]]):
                stack.append((index + 1, current + letter))
        return result
