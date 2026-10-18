# 给定一个字符串 s ，你需要反转字符串中每个单词的字符顺序，同时仍保留空格和单词的初始顺序。
# 示例 1：
# 输入：s = "Let's take LeetCode contest"
# 输出："s'teL ekat edoCteeL tsetnoc"
# 示例 2:
# 输入： s = "Mr Ding"
# 输出："rM gniD"
# 提示：
# 	1 <= s.length <= 5 * 104
# 	s 包含可打印的 ASCII 字符。
# 	s 不包含任何开头或结尾空格。
# 	s 里 至少 有一个词。
# 	s 中的所有单词都用一个空格隔开。

# leetcode submit region begin(Prohibit modification and deletion)

class Solution(object):
    def reverseWords(self, s):
        """
        :type s: str
        :rtype: str
        """
        s_list = list(s)
        n = len(s_list)
        start = 0
        
        while start < n:
            while start < n and s_list[start] == ' ':
                start += 1
            if start >= n:
                break
            end = start
            while end < n and s_list[end] != ' ':
                end += 1
            left, right = start, end - 1
            while left < right:
                s_list[left], s_list[right] = s_list[right], s_list[left]
                left += 1
                right -= 1
            start = end
        
        return ''.join(s_list)

# leetcode submit region end(Prohibit modification and deletion)
