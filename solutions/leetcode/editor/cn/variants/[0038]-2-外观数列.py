class Solution(object):
    def countAndSay(self, n):
        """
        :type n: int
        :rtype: str
        """
        if n == 1:
            return "1"
        prev = self.countAndSay(n - 1)
        result = ""
        count = 1
        current_char = prev[0]
        for i in range(1, len(prev)):
            if prev[i] == current_char:
                count += 1
            else:
                result += str(count) + current_char
                count = 1
                current_char = prev[i]
        result += str(count) + current_char
        return result
