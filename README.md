# LeetCode Solutions

个人 LeetCode 刷题记录，使用 **PyCharm CE 2024.3 + LeetCode Editor 插件** 维护，代码同步到本仓库。

> 仓库已公开（public）。分享链接：<https://github.com/Mu-sensei/leetcode>

---

## ⚠️ 代码在哪里？（解决"打开看不到代码"）

GitHub 首页只能看到根目录的几个文件。**真正的题目代码在第 4 层目录里**，需要点进去：

```
leetcode/
├── solutions/                  ← 点这里
│   └── leetcode/
│       └── editor/
│           └── cn/             ← 再点三层，所有题目代码都在这里
│               ├── [0001]两数之和.c      ← C
│               ├── [0002]两数相加.cpp    ← C++
│               ├── ...
│               └── [0557]反转字符串中的单词 III.py
├── INDEX.md                    ← 按题号 1→557 升序 + 按难度分组的题单
├── local_run.py                ← 本地运行/测试框架
├── docs/AI_SETUP.md            ← PyCharm AI 配置指南
├── .github/                    ← PR 模板
└── README.md
```

也可以直接用 `INDEX.md` 查题，或在本仓库内搜索 `[题号]`。

---

## 目录结构

| 路径 | 作用 |
| --- | --- |
| `solutions/leetcode/editor/cn/` | **题目代码本体**，由 LeetCode 插件生成/维护（文件名已 4 位补零，GitHub 列表按数值排序） |
| `INDEX.md` | 110 道已 AC 题的清单（按题号 + 按难度） |
| `local_run.py` | 本地跑通解法的脚本 |
| `docs/AI_SETUP.md` | IDE 里配 AI 辅助的教程 |
| `.github/PULL_REQUEST_TEMPLATE.md` | 提交 PR 时的描述模板 |

---

## 环境配置（LeetCode Editor 插件）

| 设置项 | 值 |
| --- | --- |
| URL | `https://leetcode.cn` |
| Temp File Path | `<本仓库绝对路径>/solutions` |
| 语言 | Python3 |
| Code FileName | `$!{question.frontendQuestionId}-$!{question.titleSlug}` |

> Temp File Path 必须落在 PyCharm 当前打开的项目目录内，否则右上角 Run / Submit 按钮不会出现。

---

## 本地运行解法

详见 [`local_run.py`](local_run.py)。基本用法：

```bash
python local_run.py 1        # 运行第 1 题的示例用例
python local_run.py 9 --list # 列出第 9 题的示例
```

> SQL 类题目（`[0175]`~`[0197]` 等 6 道）文件里是 **MySQL** 语句，无法用 Python 框架跑，请在 MySQL 环境验证。

---

## 分支与协作

- `main`：稳定分支，已通过测试的内容才合进来。
- `develop`：日常开发分支，新题/改动先提到这里，再开 PR 合到 `main`。
- 详见每次开 PR 时的模板说明。

---

## 进度

已 AC **110** 题（其中 104 道 Python + 6 道 SQL）。完整清单见 [`INDEX.md`](INDEX.md)。
