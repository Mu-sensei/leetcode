#include <iostream>

// Definition for singly-linked list.
struct ListNode {
    int val;
    ListNode *next;
    ListNode() : val(0), next(nullptr) {}
    ListNode(int x) : val(x), next(nullptr) {}
    ListNode(int x, ListNode *next) : val(x), next(next) {}
};

class Solution {
public:
    ListNode* addTwoNumbers(ListNode* l1, ListNode* l2) {
        ListNode* dummy = new ListNode(0); // 哑节点，简化操作
    ListNode* current = dummy;
    int carry = 0; // 进位

    while (l1 != nullptr || l2 != nullptr || carry != 0) {
        int sum = carry;
        if (l1 != nullptr) {
            sum += l1->val;
            l1 = l1->next;
        }
        if (l2 != nullptr) {
            sum += l2->val;
            l2 = l2->next;
        }

        carry = sum / 10; // 计算进位
        current->next = new ListNode(sum % 10); // 创建新节点存储当前位的值
        current = current->next;
    }

    ListNode* result = dummy->next;
    delete dummy; 
    return result;
    }
};

/* ---- 本地测试：g++ [0002]两数相加.cpp && ./a.out ---- */
static ListNode* build(int arr[], int n) {
    ListNode* dummy = new ListNode(0);
    ListNode* cur = dummy;
    for (int i = 0; i < n; ++i) {
        cur->next = new ListNode(arr[i]);
        cur = cur->next;
    }
    ListNode* head = dummy->next;
    delete dummy;
    return head;
}

static void printList(ListNode* l) {
    while (l != nullptr) {
        std::cout << l->val;
        if (l->next) std::cout << "->";
        l = l->next;
    }
    std::cout << std::endl;
}

int main()
{
    int a1[] = {2, 4, 3}; // 342
    int a2[] = {5, 6, 4}; // 465
    ListNode* l1 = build(a1, 3);
    ListNode* l2 = build(a2, 3);
    ListNode* res = Solution().addTwoNumbers(l1, l2);
    printList(res); // 期望: 7->0->8 (807)
    return 0;
}
