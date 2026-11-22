class Solution(object):
    def isValidSudoku(self, board):
        """
        :type board: List[List[str]]
        :rtype: bool
        """
        for row in board:
            seen = set()
            for num in row:
                if num != '.':
                    if num in seen:
                        return False
                    seen.add(num)
        for col in range(9):
            seen = set()
            for row in range(9):
                num = board[row][col]
                if num != '.':
                    if num in seen:
                        return False
                    seen.add(num)
        for i in range(0, 9, 3):
            for j in range(0, 9, 3):
                seen = set()
                for x in range(3):
                    for y in range(3):
                        num = board[i + x][j + y]
                        if num != '.':
                            if num in seen:
                                return False
                            seen.add(num)
        return True
