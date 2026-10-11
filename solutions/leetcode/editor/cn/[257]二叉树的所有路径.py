# 给你一个二叉树的根节点 root。
# 按 任意顺序 ，返回所有 从根节点到叶子节点 的路径。
# 叶子节点 是指没有子节点的节点。
# 示例 1：
# 输入：root = [1,2,3,null,5]
# 输出：["1->2->5","1->3"]
# 示例 2：
# 输入：root = [1]
# 输出：["1"]
# 提示：
# 	树中节点的数目在范围 [1, 100] 内
# 	-100 <= Node.val <= 100

# leetcode submit region begin(Prohibit modification and deletion)
# Definition for a binary tree node.
# class TreeNode(object):
#     def __init__(self, val=0, left=None, right=None):
#         self.val = val
#         self.left = left
#         self.right = right
class Solution(object):
    def binaryTreePaths(self, root):
        """
        :type root: Optional[TreeNode]
        :rtype: List[str]
        """
        
# leetcode submit region end(Prohibit modification and deletion)
