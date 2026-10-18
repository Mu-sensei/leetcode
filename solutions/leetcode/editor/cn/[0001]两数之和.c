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
int main()
{
    int nums[] = {2, 7, 11, 15};
    int target = 9;
    int returnSize = 0;
    int* r = twoSum(nums, 4, target, &returnSize);
    printf("[%d, %d]\n", r[0], r[1]); /* 期望: [0, 1] */
    free(r);
    return 0;
}
