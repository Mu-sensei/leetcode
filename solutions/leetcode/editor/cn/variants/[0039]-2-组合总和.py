class Solution(object):
    def combinationSum(self, candidates, target):
        """
        :type candidates: List[int]
        :type target: int
        :rtype: List[List[int]]
        """
        result = []
        candidates.sort()  
        def backtrack(path, start):
            current_sum = sum(path)
            if current_sum == target:
                result.append(path[:])
                return
            if current_sum > target:
                return
            for i in range(start, len(candidates)):
                path.append(candidates[i])
                backtrack(path, i)  
                path.pop()
        backtrack([], 0)
        return result
