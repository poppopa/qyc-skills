# qyc-skills

可公开使用的 Agent Skills。当前包含 **Learning Coach · 通用学习教练**（`tech-learning-coach`）与 **极客时间课程学习适配器**（`geekbang-lesson-learning`）。

它适合这样的情况：你想了解一个领域，却还不能确定自己是否感兴趣。不用一开始就承诺几周的学习计划，先看清全貌，再决定投入多少。

## 当前技能

### Learning Coach / `tech-learning-coach`

不限技术，也可用于法律诉讼流程、科学、历史、人文、经济、摄影、写作等领域。

- **全貌层**：约1～5分钟阅读，讲清主题定位、核心关系、一个例子与边界，并给出小知识图谱。
- **主线层**：你选择深入后，先协商小时级预算，再逐节讲解；默认建议约2小时，但不会擅自开课。
- **深化层**：按兴趣继续研究理论、复杂情境、实践方法或原始资料，不重复扩写前面的内容。
- **学习节奏**：练习可选，允许跳过、追问、举例和换方向；区分“已经讲过”与“已经验证理解”。

不是把知识点列成目录：流程类会讲角色、条件和分支，人文类会区分事实与解释，实践类会结合示范与判断标准。专业主题有适用范围和来源核验要求。

### 极客时间课程学习 / `geekbang-lesson-learning`

提供极客时间课程链接后，先完整读取公开介绍、所有相关“查看更多”及长图目录，再结合 `tech-learning-coach` 制定学习路线。

- **完整性先行**：核对内联展开、讲师弹层、懒加载、目录分页与图片首尾，不把文本提取成功等同于页面读全。
- **以原课程为范围**：保留原模块/原题编号到教练小节的映射；可拆合重排，但其余内容必须有选学、后续或暂缓去向。
- **沿用学习教练**：先看全貌，按已确认目标与小时预算规划；只要计划不自动开课，不启动倒计时。
- **访问边界清楚**：介绍、大纲与各讲正文分开标记；不声称读过付费正文，不购买或绕过访问限制。

依赖同一环境可读取的 `tech-learning-coach` 完整目录，以及宿主浏览器/公开全文与图片读取能力。默认走 Browser Use，具体操作加载宿主的浏览器规范；仅在符合授权边界时降级。没有教练时会说明依赖缺失，不自动安装。

## 安装

### 使用 Skills CLI

从 GitHub 安装此技能，按提示选择目标客户端：

```bash
npx skills add poppopa/qyc-skills --skill tech-learning-coach
```

使用极客时间适配器时，同时安装学习教练：

```bash
npx skills add poppopa/qyc-skills --skill tech-learning-coach --skill geekbang-lesson-learning
```

用户级安装（跨项目）：

```bash
npx skills add poppopa/qyc-skills --skill tech-learning-coach -g
```

安装前请查看 [Skills CLI 文档](https://github.com/vercel-labs/skills)，确认当前 Node.js 要求、目标客户端与安装选项。CLI 是可选安装器，不是技能运行依赖。执行 `npx` 会下载并运行安装器，请先审阅其来源与本仓库内容。

### 手动安装

1. 下载或克隆本仓库。
2. 将需要的 `skills/<技能名>/` **整个目录**复制到目标客户端的技能目录，不要只复制 `SKILL.md`；极客时间适配器需要同时保留 `tech-learning-coach/`。
3. 按客户端的技能加载方式启用，查找标识 `tech-learning-coach` 或 `geekbang-lesson-learning`。

```bash
git clone https://github.com/poppopa/qyc-skills.git
```

各客户端的技能目录、刷新和加载方式不同。本仓库提供标准的 `SKILL.md` 与相对路径资源，不承诺所有客户端都能自动发现；请参考目标客户端文档。

## 使用示例

先探索兴趣：

> 用 tech-learning-coach 带我了解 eBPF，还不确定有没有兴趣，先用3分钟讲全貌。

学习非技术流程：

> 用 tech-learning-coach 带我了解中国大陆民事诉讼的一般流程，先看3分钟全貌，只做通识学习。

条件明确，直接开课：

> 我没学过摄影，想用两小时看懂曝光并做一点练习，跳过全貌，直接开始。

继续或调整：

> 这一节换个例子。 / 不做题，继续。 / 先总结进度。 / 我想深入这个分支。

按极客时间课程规划：

> 用 geekbang-lesson-learning 读取 https://time.geekbang.org/column/intro/101189701 的完整课程描述，包含“查看更多”和图片目录；结合学习教练制定路线，先不开始授课。

> 我有 Python 基础，本轮两小时理解状态恢复；保留其他模块的后续去向，只给计划。

## 运行要求与边界

- 这是**指令型 Skill**，不是独立 Agent、插件服务或完整应用。宿主需要能读取技能文件并遵循它的指令。
- 核心授课没有运行时依赖，不需要本仓库专属API密钥或企业内网资源；可选倒计时辅助使用Python 3.9+标准库及本机浏览器，不需npm依赖。
- 启用自动计时后，每节按预计时长启动。豆包工作可在右侧浏览器显示，支持暂停、继续、重置和结束；不是原生聊天文字倒计时。仅本机可访问，默认无系统通知或音效，辅助服务最多运行8小时。
- 公开资料检索使用宿主已有的搜索/浏览能力；无法联网时，不会假装核验了最新信息。
- 结构化提问、特殊引用卡片、专业领域技能均不是硬依赖；没有这些能力时按技能中的对话和来源链接替代规则处理。
- 法律、医学、投资等课程用于学习，不替代个案专业意见，也不授予真实诉讼、治疗或交易的执行权限。
- “1～5分钟”“约2小时”是内容与学习量估算，不是实测耗时或掌握保证。
- 跨会话进度持久化依赖宿主；没有持久化能力时使用可复制的进度快照。

## 文件结构

```text
qyc-skills/
├── README.md
├── LICENSE
└── skills/
    ├── geekbang-lesson-learning/
    │   ├── SKILL.md
    │   └── references/
    │       ├── course-reading.md
    │       ├── plan-mapping.md
    │       └── acceptance-cases.md
    └── tech-learning-coach/
        ├── SKILL.md
        ├── assets/学习倒计时.html
        ├── scripts/
        │   ├── learning_timer.py
        │   └── test_learning_timer.py
        └── references/
            ├── teaching-patterns.md
            ├── public-knowledge.md
            ├── learning-timer.md
            └── acceptance-cases.md
```

## 验证状态

技能元数据、相对资源引用、文件结构和关键规则经过静态检查。学习教练含26个行为验收场景，计时器包含9项自动回归测试；极客时间适配器另含26个行为验收场景，并用示例页核验了目录展开、原始长图分段阅读与讲师弹层读取。**行为场景不是模型实测通过报告，页面读取核验也不是端到端教学验证**。不同客户端的实际学习设计、授课与计时展示仍需运行验证。

## 贡献

欢迎通过Issue反馈使用中的范围误判、讲解不清、流程遗漏或状态问题；请附脱敏的输入、预期行为和实际行为。请勿上传个人案件、病历、凭据或其他私密材料。

## 许可证

[MIT](LICENSE)，版权声明使用GitHub用户名 `poppopa`。
