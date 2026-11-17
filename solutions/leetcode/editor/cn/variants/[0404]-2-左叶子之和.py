# Definition for a binary tree node.
# class TreeNode(object):
#     def __init__(self, val=0, left=None, right=None):
#         self.val = val
#         self.left = left
#         self.right = right
class Solution(object):
    def sumOfLeftLeaves(self, root):
        """
        :type root: Optional[TreeNode]
        :rtype: int
        """
        if not root:
            return 0
        total = 0
        stack = [root]
        while stack:
            node = stack.pop()
            # 看 node 的左孩子是不是"左叶子"
            if node.left:
                if not node.left.left and not node.left.right:
                    total += node.left.val
                stack.append(node.left)   # 左孩子入栈待处理
            if node.right:
                stack.append(node.right)  # 右孩子入栈待处理
        return total
