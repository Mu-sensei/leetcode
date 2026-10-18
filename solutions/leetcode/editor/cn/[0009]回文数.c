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
int main() {
    int fails = 0;
    int r;
    r = isPalindrome(121);  printf("isPalindrome(121)  = %d  期望 1  %s\n", r, r==1?"PASS":"FAIL"); fails += (r==1)?0:1;
    r = isPalindrome(-121); printf("isPalindrome(-121) = %d  期望 0  %s\n", r, r==0?"PASS":"FAIL"); fails += (r==0)?0:1;
    r = isPalindrome(10);   printf("isPalindrome(10)   = %d  期望 0  %s\n", r, r==0?"PASS":"FAIL"); fails += (r==0)?0:1;
    return fails ? 1 : 0;
}
