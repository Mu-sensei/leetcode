# 给定两个字符串形式的非负整数 num1 和num2 ，计算它们的和并同样以字符串形式返回。
# 你不能使用任何內建的用于处理大整数的库（比如 BigInteger）， 也不能直接将输入的字符串转换为整数形式。
# 示例 1：
# 输入：num1 = "11", num2 = "123"
# 输出："134"
# 示例 2：
# 输入：num1 = "456", num2 = "77"
# 输出："533"
# 示例 3：
# 输入：num1 = "0", num2 = "0"
# 输出："0"
# 提示：
# 	1 <= num1.length, num2.length <= 104
# 	num1 和num2 都只包含数字 0-9
# 	num1 和num2 都不包含任何前导零

# leetcode submit region begin(Prohibit modification and deletion)

class Solution(object):
    def addStrings(self, num1, num2):
        """
        :type num1: str
        :type num2: str
        :rtype: str
        """
        i, j = len(num1) - 1, len(num2) - 1
        carry = 0
        result = []
        while i >= 0 or j >= 0 or carry:
            digit1 = int(num1[i]) if i >= 0 else 0
            digit2 = int(num2[j]) if j >= 0 else 0
            total = digit1 + digit2 + carry
            carry = total // 10
            result.append(str(total % 10))
            i -= 1
            j -= 1
        return ''.join(reversed(result))

# leetcode submit region end(Prohibit modification and deletion)
