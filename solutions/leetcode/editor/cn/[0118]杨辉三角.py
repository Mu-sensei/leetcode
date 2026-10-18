# 给定一个非负整数 numRows，生成「杨辉三角」的前 numRows 行。
# 在「杨辉三角」中，每个数是它左上方和右上方的数的和。
# 示例 1:
# 输入: numRows = 5
# 输出: [[1],[1,1],[1,2,1],[1,3,3,1],[1,4,6,4,1]]
# 示例 2:
# 输入: numRows = 1
# 输出: [[1]]
# 提示:
# 	1 <= numRows <= 30

# leetcode submit region begin(Prohibit modification and deletion)

class Solution(object):
    def generate(self, numRows):
        """
        :type numRows: int
        :rtype: List[List[int]]
        """
        triangle = []
        for i in range(numRows):
            row = [1] * (i + 1)
            for j in range(1, i):
                row[j] = triangle[i - 1][j - 1] + triangle[i - 1][j]
            triangle.append(row)
        return triangle

# leetcode submit region end(Prohibit modification and deletion)
