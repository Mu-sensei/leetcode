# 给你两个二进制字符串 a 和 b ，以二进制字符串的形式返回它们的和。
# 示例 1：
# 输入:a = "11", b = "1"
# 输出："100"
# 示例 2：
# 输入：a = "1010", b = "1011"
# 输出："10101"
# 提示：
# 	1 <= a.length, b.length <= 104
# 	a 和 b 仅由字符 '0' 或 '1' 组成
# 	字符串如果不是 "0" ，就不含前导零

# leetcode submit region begin(Prohibit modification and deletion)

class Solution(object):
    def addBinary(self, a, b):
        """
        :type a: str
        :type b: str
        :rtype: str
        """
        result = []
        carry = 0 
        i, j = len(a) - 1, len(b) - 1
        while i >= 0 or j >= 0 or carry:
            digit_a = int(a[i]) if i >= 0 else 0
            digit_b = int(b[j]) if j >= 0 else 0
            total = digit_a + digit_b + carry
            result.append(str(total % 2))
            carry = total // 2
            i -= 1
            j -= 1
        return ''.join(reversed(result))

# leetcode submit region end(Prohibit modification and deletion)
