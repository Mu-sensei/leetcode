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
            if node.left:
                if not node.left.left and not node.left.right:
                    total += node.left.val           
                stack.append(node.left)              
            if node.right:
                stack.append(node.right)           
        return total
