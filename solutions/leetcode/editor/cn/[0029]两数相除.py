class Solution(object):
    def divide(self, dividend, divisor):
        """
        :type dividend: int
        :type divisor: int
        :rtype: int
        """
        INT_MAX = (1 << 31) - 1
        INT_MIN = - (1 << 31)
        if dividend == INT_MIN and divisor == -1:
            return INT_MAX
        if divisor == 1:
            return dividend
        if divisor == -1:
            return -dividend
        
        sign = -1 if ((dividend >> 31) ^ (divisor >> 31)) else 1
        
        a = -abs(dividend)
        b = -abs(divisor)
        
        res = 0
        while a <= b:
            temp = b
            multiple = 1
            while a <= (temp << 1) and (temp << 1) < 0:
                temp <<= 1
                multiple <<= 1
            a -= temp
            res += multiple
        
        return -res if sign == -1 else res
