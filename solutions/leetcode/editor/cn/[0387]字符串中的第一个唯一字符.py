# 给定一个字符串 s ，找到 它的第一个不重复的字符，并返回它的索引 。如果不存在，则返回 -1 。
# 示例 1：
# 输入: s = "leetcode"
# 输出: 0
# 示例 2:
# 输入: s = "loveleetcode"
# 输出: 2
# 示例 3:
# 输入: s = "aabb"
# 输出: -1
# 提示:
# 	1 <= s.length <= 105
# 	s 只包含小写字母

# leetcode submit region begin(Prohibit modification and deletion)

class Solution(object):
    def firstUniqChar(self, s):
        """
        :type s: str
        :rtype: int
        """
        char_count = {}
        for char in s:
            if char in char_count:
                char_count[char] += 1
            else:
                char_count[char] = 1
        for i, char in enumerate(s):
            if char_count[char] == 1:
                return i
        
        return -1

# leetcode submit region end(Prohibit modification and deletion)
