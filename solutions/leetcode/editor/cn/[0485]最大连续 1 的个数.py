# 给定一个二进制数组 nums ， 计算其中最大连续 1 的个数。
# 示例 1：
# 输入：nums = [1,1,0,1,1,1]
# 输出：3
# 解释：开头的两位和最后的三位都是连续 1 ，所以最大连续 1 的个数是 3.
# 示例 2:
# 输入：nums = [1,0,1,1,0,1]
# 输出：2
# 提示：
# 	1 <= nums.length <= 105
# 	nums[i] 不是 0 就是 1.

# leetcode submit region begin(Prohibit modification and deletion)

class Solution(object):
    def findMaxConsecutiveOnes(self, nums):
        """
        :type nums: List[int]
        :rtype: int
        """
        current_count = 0
        max_count = 0
        for num in nums:
            if num == 1:
                current_count += 1
                if current_count > max_count:
                    max_count = current_count
            else:
                current_count = 0
        return max_count

# leetcode submit region end(Prohibit modification and deletion)
