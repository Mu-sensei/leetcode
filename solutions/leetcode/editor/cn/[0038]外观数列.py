class Solution(object):
    def countAndSay(self, n):
        """
        :type n: int
        :rtype: str
        """
        if n == 1:
            return "1"       
        result = "1"
        for _ in range(2, n + 1):
            stack = []
            current_char = result[0]
            count = 1
            for i in range(1, len(result)):
                if result[i] == current_char:
                    count += 1
                else:
                    stack.append(str(count) + current_char)
                    current_char = result[i]
                    count = 1
            stack.append(str(count) + current_char)
            result = ''.join(stack)       
        return result
        result += str(count) + current_char
        return result
