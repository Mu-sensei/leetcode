# 给定两个字符串 s 和 t ，判断它们是否是同构的。
# 如果 s 中的字符可以按某种映射关系替换得到 t ，那么这两个字符串是同构的。
# 每个出现的字符都应当映射到另一个字符，同时不改变字符的顺序。不同字符不能映射到同一个字符上，相同字符只能映射到同一个字符上，字符可以映射到自己本身。
# 示例 1：
# 输入：s = "egg", t = "add"
# 输出：true
# 解释：
# 字符串 s 和 t 可以通过以下方式变得相同：
# 	将 'e' 映射为 'a'。
# 	将 'g' 映射为 'd'。
# 示例 2：
# 输入：s = "f11", t = "b23"
# 输出：false
# 解释：
# 字符串 s 和 t 无法变得相同，因为 '1' 需要同时映射到 '2' 和 '3'。
# 示例 3：
# 输入：s = "paper", t = "title"
# 输出：true
# 提示：
# 	1 <= s.length <= 5 * 104
# 	t.length == s.length
# 	s 和 t 由任意有效的 ASCII 字符组成

# leetcode submit region begin(Prohibit modification and deletion)

class Solution(object):
    def isIsomorphic(self, s, t):
        """
        :type s: str
        :type t: str
        :rtype: bool
        """
        if len(s) != len(t):
            return False
        s_to_t = {}
        t_to_s = {}
        for i in range(len(s)):
            if s[i] in s_to_t:
                if s_to_t[s[i]] != t[i]:
                    return False
            else:
                s_to_t[s[i]] = t[i]
            if t[i] in t_to_s:
                if t_to_s[t[i]] != s[i]:
                    return False
            else:
                t_to_s[t[i]] = s[i]
        return True

# leetcode submit region end(Prohibit modification and deletion)
