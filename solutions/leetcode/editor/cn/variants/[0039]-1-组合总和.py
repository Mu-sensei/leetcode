class Solution(object):
    def combinationSum(self, candidates, target):
        """
        :type candidates: List[int]
        :type target: int
        :rtype: List[List[int]]
        """
        res = []
        candidates.sort()
        stack = [(0, 0, [])]
        while stack:
            cur_sum, start, path = stack.pop()
            if cur_sum == target:
                res.append(path)
                continue
            for i in range(len(candidates) - 1, start - 1, -1):
                num = candidates[i]
                if cur_sum + num > target:
                    continue
                stack.append((cur_sum + num, i, path + [num]))
        return res
