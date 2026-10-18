# 给你一个整数数组 nums 和一个整数 k ，判断数组中是否存在两个 不同的索引 i 和 j ，满足 nums[i] == nums[j] 且 abs(i - j) <= k 。如果存在，返回 true ；否则，返回 false 。
# 示例 1：
# 输入：nums = [1,2,3,1], k = 3
# 输出：true
# 示例 2：
# 输入：nums = [1,0,1,1], k = 1
# 输出：true
# 示例 3：
# 输入：nums = [1,2,3,1,2,3], k = 2
# 输出：false
# 提示：
# 	1 <= nums.length <= 105
# 	-109 <= nums[i] <= 109
# 	0 <= k <= 105

# leetcode submit region begin(Prohibit modification and deletion)

class Solution(object):
    def containsNearbyDuplicate(self, nums, k):
        """
        :type nums: List[int]
        :type k: int
        :rtype: bool
        """
        index_map = {}
        for i, num in enumerate(nums):
            if num in index_map:
                if i - index_map[num] <= k:
                    return True
            index_map[num] = i
        return False

# leetcode submit region end(Prohibit modification and deletion)
