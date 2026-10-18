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
int main() {
    int fails = 0;
    int r;
    r = romanToInt("III");     printf("romanToInt(\"III\")     = %d  期望 3    %s\n", r, r==3?"PASS":"FAIL");    fails += (r==3)?0:1;
    r = romanToInt("IV");      printf("romanToInt(\"IV\")      = %d  期望 4    %s\n", r, r==4?"PASS":"FAIL");    fails += (r==4)?0:1;
    r = romanToInt("MCMXCIV"); printf("romanToInt(\"MCMXCIV\") = %d  期望 1994 %s\n", r, r==1994?"PASS":"FAIL"); fails += (r==1994)?0:1;
    return fails ? 1 : 0;
}
