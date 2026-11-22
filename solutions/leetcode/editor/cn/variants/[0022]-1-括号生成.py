class Solution(object):
    def generateParenthesis(self, n):
        """
        :type n: int
        :rtype: List[str]
        """
        result = []
        stack = [(0, 0, "")]
        while stack:
            left, right, current = stack.pop()
            if left == n and right == n:
                result.append(current)
                continue
            if right < left:
                stack.append((left, right + 1, current + ')'))
            if left < n:
                stack.append((left + 1, right, current + '('))
        return result
