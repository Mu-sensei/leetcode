#include <stdio.h>
#include <stdlib.h>

/**
 * Note: The returned array must be malloced, assume caller calls free().
 */
int* twoSum(int* nums, int numsSize, int target, int* returnSize)
{
    for (int i = 0; i < numsSize;i++){
        for (int j = i+1;j<numsSize;j++){
            if (nums[i]+nums[j]==target){
                int* ret =malloc(sizeof(int)*2);
                ret[0] = i,ret[1] = j;
                *returnSize = 2;
                return ret; 
            }
        }
    }
    *returnSize = 0;
    return NULL;
}

/* ---- 本地测试：gcc [0001]两数之和.c && ./a.out ---- */
static int check(int* nums, int n, int target, int e0, int e1) {
    int returnSize = 0;
    int* r = twoSum(nums, n, target, &returnSize);
    int ok = (returnSize == 2 && r[0] == e0 && r[1] == e1);
    printf("twoSum(..., %d) = [%d, %d]  期望 [%d, %d]  %s\n",
           target, r[0], r[1], e0, e1, ok ? "PASS" : "FAIL");
    free(r);
    return ok ? 0 : 1;
}

int main() {
    int fails = 0;
    int a1[] = {2, 7, 11, 15};   fails += check(a1, 4, 9, 0, 1);
    int a2[] = {3, 2, 4};        fails += check(a2, 3, 6, 1, 2);
    int a3[] = {-1, -2, -3, -4}; fails += check(a3, 4, -7, 2, 3);
    return fails ? 1 : 0;
}
