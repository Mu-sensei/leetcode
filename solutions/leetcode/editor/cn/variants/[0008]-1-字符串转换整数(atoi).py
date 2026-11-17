class Solution(object):
    def myAtoi(self, s):
        """
        :type s: str
        :rtype: int
        """
        INT_MIN = -2**31
        INT_MAX = 2**31 - 1
        s = s.lstrip()
        if not s:
            return 0
        sign = 1
        start = 0
        if s[0] == '-':
            sign = -1
            start = 1
        elif s[0] == '+':
            start = 1
        num = 0
        for i in range(start, len(s)):
            if s[i].isdigit():
                num = num * 10 + int(s[i])
                if num > INT_MAX:
                    break
            else:
                break
        num = sign * num
        INT_MIN = -2**31
        INT_MAX = 2**31 - 1
        if num < INT_MIN:
            return INT_MIN
        elif num > INT_MAX:
            return INT_MAX
        return num
