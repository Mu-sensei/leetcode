# PyCharm 里的 AI 配置指南

本指南针对你的环境：**macOS（Intel Mac）+ PyCharm CE 2024.3**。目标是在 IDE 里接上 AI 辅助编程（补全、对话、解释代码）。

---

## 方案对比

| 方案 | 提供方 | 免费额度 | 需要账号 | 备注 |
| --- | --- | --- | --- | --- |
| **JetBrains AI Assistant** | JetBrains 官方 | 有免费档（需 JetBrains 账号） | JetBrains Account | 内置集成好，2024.3 起叫 AI Assistant；新出的 **Junie** 是 Agent 式编程 |
| **GitHub Copilot** | GitHub / OpenAI | 学生/开源维护者免费，否则付费 | GitHub 账号 | 补全最成熟，插件名 "GitHub Copilot" |
| **本地模型（Ollama + 插件）** | 社区 | 完全免费、离线 | 无 | 用本机跑小模型（如 qwen2.5-coder），隐私好但 Intel Mac 独显弱、速度一般 |

> 你这台是 2019 Intel Mac + AMD 独显 4G，本地跑大模型体验一般，**优先推荐 JetBrains AI Assistant 或 Copilot**（走云端，不吃本地算力）。

---

## 方式 A：JetBrains AI Assistant（推荐，集成最顺）

1. 打开 PyCharm → 顶部菜单 **Settings**（`⌘,`）→ **Plugins** → **Marketplace**。
2. 搜索 **`AI Assistant`**（或 `Junie`），点 **Install**，装完 **Restart IDE**。
3. 重启后右侧/顶部出现 AI 图标。首次使用会让你登录 **JetBrains Account**（没有就注册一个，免费）。
4. 登录后：
   - 选中代码 → 右键 **AI** → "Explain"（解释）/ "Refactor"（重构）。
   - 侧边 **AI Assistant** 工具窗可直接对话，例如："帮我把 [0001]两数之和 改成哈希表解法"。
5. 免费档有用量上限，够日常用；要无限制需订阅（可选）。

---

## 方式 B：GitHub Copilot

1. **Settings → Plugins → Marketplace** 搜索 **`GitHub Copilot`** 安装并重启。
2. 首次会跳浏览器让你用 **GitHub 账号**授权（你的 `Mu-sensei` 账号即可）。
3. 授权后，写代码时会有灰色补全建议，按 `Tab` 接受。
4. 对话功能在 **Copilot Chat** 工具窗（单独插件 `GitHub Copilot Chat`，一起装）。
5. 费用：个人版付费；如果你是学生或开源维护者，可申请免费（GitHub Education / 维护者计划）。

---

## 方式 C：本地模型（Ollama，离线免费）

适合不想上传代码到云端的场景。

1. 装 [Ollama](https://ollama.com)（mac 直接下 dmg）。
2. 拉一个代码模型：终端跑 `ollama pull qwen2.5-coder:7b`（7B 在 4G 显存勉强，建议用 3B/1.5B 更流畅）。
3. PyCharm 装插件 **`Continue`** 或 **`CodeGPT`**，在插件设置里选 "Ollama" 并填模型名。
4. 缺点：Intel Mac 没 NVIDIA CUDA，Ollama 在 macOS 走 Metal（AMD 独显不加速，靠核显/CPU），速度慢，仅适合轻量补全。

---

## 针对本项目的实用建议

- 写 LeetCode 解法时，可以让 AI 帮你：**生成测试用例**、**解释某题最优解**、**把解法改成另一种思路**（动态规划→贪心等）。
- 注意：AI 生成的代码务必自己跑 `local_run.py <题号>` 验证后再提交，别直接信。
- **不要把你的 LeetCode cookie / GitHub Token 贴进聊天或写进文件**（本仓库 `.gitignore` 已挡住常见敏感文件，但自己也要留意）。

---

## 排错

- 装完插件看不到 AI 入口 → 确认 **Restart IDE** 过；再查 `Settings → Plugins → Installed` 里勾选框是否打上。
- 登录循环/授权失败 → 检查网络能否访问 `account.jetbrains.com` 或 `github.com`；公司网络可能被墙，换网络或走方式 C。
- Copilot 没补全 → 确认右下角 Copilot 图标是彩色（已登录），不是灰色。
