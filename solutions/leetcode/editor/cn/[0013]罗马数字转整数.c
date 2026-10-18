#include <stdio.h>
#include <string.h>

int romanToInt(char* s) {
    int symbolValues[26];
    symbolValues['I' - 'A'] = 1;
    symbolValues['V' - 'A'] = 5;
    symbolValues['X' - 'A'] = 10;
    symbolValues['L' - 'A'] = 50;
    symbolValues['C' - 'A'] = 100;
    symbolValues['D' - 'A'] = 500;
    symbolValues['M' - 'A'] = 1000;
    int ans = 0;
    int n = strlen(s);
    for (int i = 0; i < n; ++i) {
        int value = symbolValues[s[i] - 'A'];
        if (i < n - 1 && value < symbolValues[s[i + 1] - 'A']) {
            ans -= value;
        } else {
            ans += value;
        }
    }
    return ans;
}

/* ---- 本地测试：gcc [0013]罗马数字转整数.c && ./a.out ---- */
int main()
{
    printf("%d\n", romanToInt("III"));      /* 3    */
    printf("%d\n", romanToInt("IV"));       /* 4    */
    printf("%d\n", romanToInt("MCMXCIV"));  /* 1994 */
    return 0;
}
