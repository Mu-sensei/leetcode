# 由 LeetCode 网页提交同步 (submission 759882886)
class Solution(object):
    def reverse(self, x):
        """
        :type x: int
        :rtype: int
        """
        sign = 1 if x >= 0 else -1
        x = abs(x)
        result = 0
        while x != 0:
            digit = x % 10
            if result > (2**31 - 1) // 10 or (result == (2**31 - 1) // 10 and digit > 7):
                return 0
            if result < -2**31 // 10 or (result == -2**31 // 10 and digit < -8):
                return 0
            result = result * 10 + digit
            x = x // 10
        return sign * result
