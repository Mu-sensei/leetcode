#include <stdio.h>
#include <stdbool.h>

bool isPalindrome(int x) {
    if(x<0) return false;
    long x1=x,y=0l;
    while(x1){
        y=y*10+x1%10;
        x1/=10;
    }
    return x==y;
}

/* ---- 本地测试：gcc [0009]回文数.c && ./a.out ---- */
int main()
{
    printf("%d\n", isPalindrome(121));   /* 1 (true)  */
    printf("%d\n", isPalindrome(-121));  /* 0 (false) */
    printf("%d\n", isPalindrome(10));    /* 0 (false) */
    return 0;
}
