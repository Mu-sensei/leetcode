# 给定两个字符串 s 和 t ，编写一个函数来判断 t 是否是 s 的 字母异位词。
# 示例 1:
# 输入: s = "anagram", t = "nagaram"
# 输出: true
# 示例 2:
# 输入: s = "rat", t = "car"
# 输出: false
# 提示:
# 	1 <= s.length, t.length <= 5 * 104
# 	s 和 t 仅包含小写字母
# 进阶: 如果输入字符串包含 unicode 字符怎么办？你能否调整你的解法来应对这种情况？

# leetcode submit region begin(Prohibit modification and deletion)

class Solution(object):
    def isAnagram(self, s, t):
        """
        :type s: str
        :type t: str
        :rtype: bool
        """
        if len(s) != len(t):
            return False
        s_count = {}
        for char in s:
            if char in s_count:
                s_count[char] += 1
            else:
                s_count[char] = 1
        t_count = {}
        for char in t:
            if char in t_count:
                t_count[char] += 1
            else:
                t_count[char] = 1
        return s_count == t_count

# leetcode submit region end(Prohibit modification and deletion)
