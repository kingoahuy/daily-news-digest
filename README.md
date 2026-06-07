# Daily News Digest V5

一个可本地运行的个人 AI 新闻雷达。程序从 RSS 获取新闻标题和摘要，执行规则
评分、候选新闻 AI 重要性评分、主题聚类、阈值过滤和个人偏好排序，再生成精简
Markdown 简报。V5 默认输出中文，双语模式可在网页设置中重新开启。日报可以发送
到邮箱、导出到 GitHub Pages，也会保存到 SQLite，供 Streamlit 网页端查看、
搜索和互动。

项目只使用 RSS 提供的标题、摘要、发布时间、来源和链接，不抓取新闻全文。

## V2 功能

- 科技、财经、体育、社会、政治五大分类
- 重点关注 AI、大模型、半导体、股市、斯诺克、网球、乒乓球、NBA 和足球
- 24/48 小时时效评分、类别权重、兴趣关键词和多来源加分
- 详细的九段式中文新闻简报
- DeepSeek 不可用时自动生成带来源的 fallback 简报
- SQLite 保存日报、新闻条目、邮件状态、评价和用户偏好
- Streamlit 查看今日日报与历史日报
- 对新闻评分、打标签和记录阅读感受
- 根据历史反馈调整后续新闻排序
- 保留 SMTP 邮件发送和 GitHub Actions 定时运行

## V3 网页体验优化

V3 将网页端升级为主页面卡片导航，不再依赖侧边栏切换主要功能。首页展示
今日日报状态、新闻数量、互动统计与下一次本地邮件时间，并提供以下入口：

- **今日日报**：阅读最新的完整简报
- **历史日报**：按关键词、分类和日期回看报告
- **新闻互动**：对最近或历史日报中的新闻点赞、收藏和评论
- **我的收藏**：搜索和筛选收藏过的新闻
- **我的偏好画像**：查看互动如何改变分类和关键词权重
- **邮件推送设置**：配置本地每日发送时间
- **手动生成日报**：立即运行现有 `--dry-run` 流程

### 点赞、收藏与评论

每条新闻卡片底部提供：

- `👍 点赞`：再次点击可取消，给分类和关键词增加小幅权重
- `⭐ 收藏`：再次点击可取消，权重高于点赞，并加强来源偏好
- `💬 评论`：保存阅读想法，可添加多条评论

评论中出现“重要、继续关注、喜欢、对我有用、深入分析”等词时，系统会提高
相关分类和关键词权重；出现“不感兴趣、以后少推、无聊、重复、没价值”等词时，
系统会降低相关权重。算法是简单、透明的规则，不是黑盒机器学习。

互动保存在 SQLite 的 `news_interactions` 表中，旧的 `feedback` 数据不会删除。
下一次运行 `python -m src.main --dry-run` 或 `--send` 时，新闻排序会自动读取新旧
两类偏好。

### 设置本地邮件时间

在网页首页进入“邮件推送设置”，可以保存：

- 邮件推送开关
- 每日发送时间，默认 `08:13`
- 时区，默认 `Asia/Singapore`
- 本地自动发送开关

设置保存在 SQLite 的 `user_settings` 表。页面不会显示 API Key、邮箱密码或
SMTP 授权码。

### 启用本地邮件定时发送

最简单的方式是在网页设置中开启“本地自动发送”，保存后重新运行：

```powershell
python scripts/start_web.py
```

网页守护器会同时启动一个本地邮件调度器。也可以单独运行：

```powershell
python scripts/local_mail_scheduler.py
```

调度器每 60 秒检查一次设置；到达设定时间且当天尚未成功发送时，会执行：

```powershell
python -m src.main --send
```

运行记录保存在 `local_scheduler_runs` 表，日志位于：

```text
logs/local_mail_scheduler.log
```

停止 `python scripts/start_web.py` 启动的网页服务时：

```powershell
python scripts/stop_web.py
```

与网页一起启动的本地调度器也会停止。

### 本地调度与 GitHub Actions 的区别

网页设置的发送时间只用于本地调度器：

1. 电脑必须开机；
2. 网页守护服务或 `local_mail_scheduler.py` 必须保持运行；
3. 电脑关机或进程停止时，本地定时邮件不会发送；
4. GitHub Actions 的发送时间仍由
   `.github/workflows/daily_news.yml` 中的 cron 控制；
5. 本地网页不会修改 GitHub Actions 工作流；
6. 若要让云端读取网页设置，需要后续接入云数据库或同步配置，本次没有实现。

### V3 常见问题

**点赞或收藏后何时影响推荐？**

互动会立即写入数据库，下一次生成日报时用于排序。

**为什么本地设置了时间却没有收到邮件？**

检查本地自动发送和邮件推送两个开关是否都开启、电脑是否开机、网页守护器或
调度器是否运行，并查看 `logs/local_mail_scheduler.log`。还要确认 `.env` 中的
SMTP 配置完整。

**修改网页时间会改变 GitHub Actions 吗？**

不会。GitHub Actions 需要单独修改 workflow 中的 cron。

**如何手动测试而不发送邮件？**

```powershell
python -m src.main --dry-run
```

**如何手动发送邮件？**

```powershell
python -m src.main --send
```

## 参考 Horizon 后的 V4 升级

V4 借鉴 Horizon 的配置驱动流水线、AI 重要性评分、阈值过滤、重点新闻二次补充、
双语输出和静态站发布思路，但没有复制其代码，也没有引入 Twitter/X、Telegram、
MCP、向量数据库、全文抓取或复杂订阅系统。现有 RSS、邮件、SQLite、Streamlit、
互动偏好和本地调度器全部保留。

### 什么是 AI 新闻雷达

“新闻雷达”不再只按 RSS 时间顺序整理内容，而是执行：

1. URL 和标题初步去重；
2. 本地可解释规则评分；
3. DeepSeek 批量重要性评分；
4. 相似标题与关键词主题聚类；
5. 按阈值过滤低价值内容；
6. 将点赞、收藏、评论形成的偏好加入最终排序；
7. 对 1-3 条核心新闻生成保守的双语背景补充；
8. 生成完整中英文双语日报。

每条新闻保存 `ai_score`、`ai_reason`、`ai_summary`、`ai_tags` 和
`importance_tier`。AI 调用失败时自动使用规则分，不会因一批失败而中断日报。

### 新闻去重与主题聚类

`src/deduplicator.py` 使用规范化 URL、`difflib` 标题相似度和简单标题关键词判断
同一事件。每个主题簇保留一条代表新闻，同时保留其他来源链接。多个独立来源报道
同一事件时会增加聚类分，但多来源本身不等于事实已经完全确认。

### 核心新闻背景补充

`src/enricher.py` 默认只处理最高分的 1-3 条新闻。它只使用 RSS 标题、摘要、
来源、链接和同主题来源，不抓取新闻全文，也不强依赖 Web Search。信息不足时会
明确说明无法判断；政治内容保持中立，财经内容不构成投资建议。

### V4 配置中心

- `config/app.yaml`：项目标题、时区和双语输出设置
- `config/sources.yaml`：RSS 来源、分类和启用状态
- `config/filtering.yaml`：时间窗口、评分阈值、批次大小和分类权重
- `config/delivery.yaml`：邮件、本地网页、GitHub Pages 和预留 Webhook 开关
- `config/preferences.yaml`：初始个人偏好

真实 API Key、SMTP 密码和邮箱授权码仍然只从 `.env` 或 GitHub Secrets 读取。
YAML 中只保存普通设置或环境变量名。

常用过滤配置：

```yaml
time_window_hours: 36
ai_score_threshold: 6.5
core_topic_threshold: 7.5
max_items_per_category: 6
max_enriched_items: 3
ai_batch_size: 10
ai_max_retries: 3
enable_ai_scoring: true
enable_deduplication: true
enable_enrichment: true
```

关闭 AI 评分时将 `enable_ai_scoring` 改为 `false`。评分批次最大为 10 条，失败
最多重试 3 次。降低 `ai_score_threshold` 会增加进入日报的新闻数量。

### 中英文双语日报

V4 生成的本地 Markdown、邮件正文、数据库日报和 GitHub Pages 归档均为中英文
双语版。每个主要章节先显示中文，再显示对应英文；两个语言版本使用相同来源和
事实边界。DeepSeek 不可用时，本地 fallback 也会保留双语结构。
V4 之前已经生成的历史 Markdown 不会被自动翻译或改写。

### GitHub Pages 静态日报

手动导出：

```powershell
python -m src.main --dry-run --export-pages
```

也可以单独重建静态归档：

```powershell
python -m src.pages_exporter
```

命令会把 `reports/*.md` 复制到 `docs/reports/`，并更新 `docs/index.md` 和
`docs/_config.yml`。它不会复制 `.env`、数据库或日志。

在 GitHub 中开启自动发布：

1. 打开仓库 `Settings -> Pages`；
2. 将 `Build and deployment -> Source` 设为 `GitHub Actions`；
3. 打开 `Settings -> Secrets and variables -> Actions -> Variables`；
4. 新建仓库变量 `ENABLE_GITHUB_PAGES`，值设为 `true`；
5. 确保 Actions 的 Workflow permissions 允许写入仓库内容；
6. 手动运行一次 `Daily News Digest`，或等待下次定时任务。

Actions 会按当前语言设置生成日报、提交 `docs/` 归档，再由独立的
`deploy-pages` 任务发布。
Pages 未开启时不要设置该变量，原有每日邮件任务仍会独立运行。

### Streamlit 与 GitHub Pages 的区别

- Streamlit 是本地交互应用，支持点赞、收藏、评论、偏好画像、邮件设置和雷达统计；
- GitHub Pages 是只读静态归档，适合随时访问历史日报；
- Pages 不读取本地 SQLite，因此不会显示私人互动数据；
- Actions 中的临时数据库不会自动同步回本地电脑。

### V4 常见问题排查

**AI 分数为空或全部使用规则分**

检查 `DEEPSEEK_API_KEY`、模型名、网络和 `enable_ai_scoring`。日志只显示异常类型，
不会打印 Key。

**日报新闻太少**

降低 `config/filtering.yaml` 中的 `ai_score_threshold`，或增加
`time_window_hours` 和 RSS 来源。

**背景补充较保守**

这是预期行为。当前版本不读取全文、不搜索网页，只能依据 RSS 已有摘要。

**Pages 没有部署**

检查 Pages Source 是否为 GitHub Actions、仓库变量是否为字符串 `true`、Actions
是否有写权限，并查看 `deploy-pages` 任务。

## V5：iOS 风格界面与省 API 模式

V5 在 V4 流程上做增量优化，没有删除 Streamlit 页面、互动、数据库、邮件、
GitHub Actions、主题聚类或背景补充。主要变化是更轻的网页界面、更少的默认新闻
数量，以及只对高潜力候选新闻调用 DeepSeek。

### 网页界面

- 全局使用 Apple 系统字体栈，并兼容苹方、微软雅黑和 Segoe UI；
- 页面背景为浅灰色，卡片为半透明白色、18-24px 圆角和轻阴影；
- 首页指标和功能入口改为紧凑的小组件卡片；
- 新闻标题默认最多显示约 80 个字符，摘要最多约 180 个字符；
- AI 理由、AI 摘要、主题簇、背景补充、后续看点和已有评论放入折叠区；
- 长标题、URL、英文单词、标签、Markdown 和表格均允许换行或横向滚动；
- 原始完整标题、链接和数据库内容不会因页面截断而改变。

### 省 API 流程

默认流程为：

1. 抓取并初步去重；
2. 对所有新闻执行本地规则评分；
3. 只取规则分最高的 40 条进入 AI 精评；
4. AI 精评后执行主题聚类和个人偏好排序；
5. 每类最多保留 3 条，总计最多保留 12 条；
6. 传给日报模型的 Top 新闻最多 8 条；
7. 默认只对 1 条核心新闻做背景补充；
8. 日报默认输出中文精简版。

未进入 AI 候选池的新闻会标记为“未进入 AI 精评，使用本地规则评分”，不会被
误记为 API 失败。按常见的 250-300 条抓取规模估算，AI 评分对象从全部新闻降为
最多 40 条；按每批 6 条计算，通常约 7 批评分请求，另加 1 次背景补充和 1 次
日报生成。

### 推荐配置

```yaml
time_window_hours: 24
ai_score_threshold: 7.2
core_topic_threshold: 8.0
max_items_per_category: 3
max_total_news: 12
max_top_news: 8
pre_ai_prefilter_limit: 40
max_enriched_items: 1
ai_batch_size: 6
ai_max_retries: 2
enable_bilingual_report: false
low_api_mode: true
ai_scoring_mode: "top_candidates_only"
```

可以直接修改 `config/filtering.yaml`。也可以在 Streamlit 首页进入“设置”，调整：

- 省 API 模式；
- 新闻总数和每类上限；
- AI 精评候选数量；
- 中文或中英文双语日报；
- 背景补充开关和数量。

网页设置保存在本机 SQLite 的 `user_settings` 表，并在下一次运行主流程时覆盖
对应 YAML 默认值。关闭“省 API 模式”会恢复对去重后全部新闻执行 AI 评分。
重新开启双语日报时，只需打开“设置 -> 双语日报”并保存。

### V5 测试

```powershell
python -m src.main --dry-run
streamlit run app.py
```

需要同时更新 GitHub Pages 时：

```powershell
python -m src.main --dry-run --export-pages
```

`.env`、SMTP 授权码、API Key、SQLite 数据库和本地日志不会进入 Pages 导出。

## shadcn/ui 风格界面

原有 Python + Streamlit 页面继续保留，并通过 CSS 参考 shadcn/ui 的设计语言。
正式的 Next.js + TypeScript + Tailwind CSS + shadcn/ui 前端现已作为独立的
`web/` 子项目加入；两个界面可以同时运行，当前不会互相替换。

统一设计系统位于 `src/ui_styles.py`，集中提供：

- 浅色与基础深色 design tokens；
- Apple 系统字体栈；
- Card、Button、Badge、Form、Alert 和 Empty State 样式；
- `clamp_text()` 与 `clamp_title()` 文本截断；
- Badge、Card Header 和 Metric Card HTML 组件函数；
- 长标题、长链接、标签、Markdown 与表格的溢出保护。

当前首页、新闻卡片、AI 雷达、偏好画像、邮件与生成设置、日报摘要均使用统一
组件风格。Card 按 Header、Title、Description、Content 和 Footer 分层；新闻
分类、AI 分数、重要性等级、点赞与收藏状态使用 Badge 展示；AI 分析与背景默认
折叠，不会增加首屏阅读压力。

Streamlit 继续负责现有本地互动与设置，Next.js 先负责现代化静态阅读和分析
原型。后端、SQLite、邮件、互动、GitHub Actions 和新闻生成流程均未迁移；
后续可通过稳定 API 将 `web/` 接到现有 Python 能力。

## Next.js 现代前端预览

项目现在新增独立的 `web/` 前端，不替换 Streamlit，也不改动 Python 抓取、
DeepSeek、邮件、SQLite 或 GitHub Actions 流程。当前版本使用静态 mock 数据，
用于先确认页面结构和视觉体验，后续可通过 API 接入真实日报。

技术栈：

- Next.js App Router + TypeScript
- Tailwind CSS
- shadcn/ui
- Recharts / shadcn Charts
- 桌面侧栏与移动端底部导航

页面：

- `/`：今日新闻 Dashboard、核心议题、分类新闻和中英文切换
- `/news/[slug]`：摘要、重要性、背景、相关链接和新手解释
- `/analytics`：分类数量、重要新闻趋势和来源占比
- `/settings`：关注分类、推送时间、语言和摘要风格 mock 设置

安装依赖并运行开发模式：

```powershell
cd web
npm install
npm run dev
```

生产构建：

```powershell
cd web
npm run lint
npm run typecheck
npm run build
```

项目提供独立守护器，默认在 `http://localhost:3000` 启动生产版本：

```powershell
python scripts/start_frontend.py
python scripts/status_frontend.py
python scripts/stop_frontend.py
```

同时启动 Streamlit 和 Next.js：

```powershell
python scripts/start_all.py
```

同时停止：

```powershell
python scripts/stop_all.py
```

VS Code 的文件夹打开任务会自动调用 `start_all.py`，重复执行不会启动重复的本
项目进程。Next.js 与 Streamlit 都有独立状态文件和异常重启机制。

### Windows 开机登录自启

安装当前 Windows 用户的登录自启项：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_startup.ps1
```

它会在当前用户 Startup 目录写入 `DailyNewsDigest.cmd`。下次电脑开机并登录
Windows 后，会自动恢复 Streamlit、Next.js 和已启用的本地邮件调度器。

移除自启：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/uninstall_startup.ps1
```

本地网站在电脑关机期间无法访问；“开机自启”表示下次登录 Windows 后自动恢复。
若需要电脑关机后仍可从互联网访问，需要把前端和后端部署到云服务器。

## 项目结构

```text
daily-news-digest/
├── app.py
├── config/
│   ├── app.yaml
│   ├── delivery.yaml
│   ├── feeds.yaml
│   ├── filtering.yaml
│   ├── sources.yaml
│   └── preferences.yaml
├── docs/
│   ├── index.md
│   └── reports/
├── data/
│   └── news_digest.db          # 本地运行后生成，不提交到 Git
├── prompts/
│   ├── daily_report_prompt.txt
│   ├── news_enrichment_prompt.txt
│   ├── news_scoring_prompt.txt
│   └── preference_summary_prompt.txt
├── reports/
├── scripts/
│   ├── local_mail_scheduler.py
│   ├── start_web.py
│   ├── status_web.py
│   └── stop_web.py
├── src/
│   ├── ui_styles.py
│   ├── ai_scorer.py
│   ├── config.py
│   ├── database.py
│   ├── deduplicator.py
│   ├── enricher.py
│   ├── fetcher.py
│   ├── formatter.py
│   ├── llm.py
│   ├── main.py
│   ├── models.py
│   ├── pages_exporter.py
│   ├── preference.py
│   ├── ranker.py
│   ├── sender.py
│   └── web_utils.py
├── .github/workflows/daily_news.yml
├── .env.example
├── .gitignore
└── requirements.txt
```

## 安装

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

macOS/Linux：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置

复制环境变量模板：

```powershell
Copy-Item .env.example .env
```

至少设置：

```dotenv
DEEPSEEK_API_KEY=your_deepseek_api_key
```

发送邮件时还需要：

```dotenv
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=your_email_smtp_auth_code
MAIL_FROM=your_email@qq.com
MAIL_TO=receiver_email@qq.com
```

`SMTP_PASSWORD` 应填写邮箱服务商生成的 SMTP 授权码，不是网页登录密码。
`.env` 已在 `.gitignore` 中，不能提交到 GitHub。

可选配置：

| 环境变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 地址 |
| `DEEPSEEK_MODEL` | `deepseek-v4-flash` | 模型名称 |
| `TIMEZONE` | `Asia/Singapore` | 日报日期时区 |
| `MAX_NEWS_PER_CATEGORY` | `8` | 每类最多保留条数 |
| `NEWS_LOOKBACK_HOURS` | `24` | RSS 回看小时数 |
| `DATABASE_PATH` | `data/news_digest.db` | SQLite 路径 |
| `SOURCES_PATH` | `config/sources.yaml` | V4 RSS 配置路径 |
| `FEEDS_PATH` | `config/feeds.yaml` | 旧版 RSS 配置兼容路径 |
| `PREFERENCES_PATH` | `config/preferences.yaml` | 初始偏好路径 |

## 运行日报

只生成日报，不发邮件：

```powershell
python -m src.main --dry-run
```

生成并发送邮件：

```powershell
python -m src.main --send
```

执行后会：

1. 抓取并清理 RSS；
2. 根据时效、兴趣和历史反馈排序；
3. 生成 Markdown 与 HTML；
4. 保存 `reports/daily_news_YYYY-MM-DD.md`；
5. 写入 `data/news_digest.db`；
6. 在 `--send` 模式下发送邮件；
7. 回写 `reports.email_sent`。

数据库写入失败只会产生警告，不会阻断原有邮件流程。邮件失败时，数据库中的
`email_sent` 会保持为 `0`。

## 本地网页端自动运行

Streamlit 网页端是本项目的本地新闻知识库，可以查看今日日报与历史日报、
评价新闻、查看偏好画像并调整分类权重。设置页不会显示 API Key、邮箱密码或
SMTP 授权码。

网页包含：

- **首页：今日日报**：查看完整简报、核心议题、生成时间和邮件状态
- **历史日报**：按关键词和分类筛选，下载 Markdown
- **新闻评价**：评分、标签、自定义标签和评价笔记
- **我的偏好画像**：查看类别权重、历史平均评分和关键词倾向
- **手动生成日报**：从网页调用现有 `--dry-run` 流程
- **设置**：查看安全配置状态并调整分类权重

### 一键启动

在项目根目录运行：

```powershell
python scripts/start_web.py
```

脚本会在后台启动并守护 Streamlit。默认网页地址是：

```text
http://localhost:8501
```

如果 `8501` 已被其他程序占用，会自动尝试 `8502`、`8503` 等可用端口。
终端会明确显示本次实际访问地址。

启动脚本会：

- 检查 `app.py`、Python 环境和 Streamlit
- 优先使用当前虚拟环境或项目 `.venv`
- 检查旧状态、PID 和网页健康状态
- 避免重复启动同一项目
- 保存状态到 `.runtime/web_status.json`
- 保存脱敏日志到 `logs/streamlit_web.log`
- 网页异常退出后自动重启，连续失败 5 次后停止

### 查看状态

```powershell
python scripts/status_web.py
```

运行中会显示网页地址、Streamlit PID 和日志文件。

### 打开网页

```powershell
python scripts/open_web.py
```

网页运行时，此命令会使用 Windows 默认浏览器打开实际地址。

### 停止网页

```powershell
python scripts/stop_web.py
```

停止脚本只会结束状态文件中属于当前项目的 Streamlit 与守护进程，不会按名称
批量结束其他 Python 进程。

### VS Code 自动启动

项目的 `.vscode/tasks.json` 已把“启动新闻知识库网页”配置为文件夹打开任务。
第一次打开项目时，VS Code 可能询问是否允许自动任务，请选择允许。也可以通过：

```text
Ctrl + Shift + P
Tasks: Manage Automatic Tasks in Folder
Allow Automatic Tasks in Folder
```

允许后，下次用 VS Code 打开这个项目文件夹，网页会自动启动。启动脚本会检测
现有状态，因此反复打开项目不会重复启动多个 Streamlit 进程。

### VS Code 手动一键启动

如果当前 VS Code 版本、工作区信任设置或自动任务权限阻止自动启动：

```text
Ctrl + Shift + P
Tasks: Run Task
启动新闻知识库网页
```

同一任务列表中还提供停止网页、查看状态、打开网页、生成日报和发送邮件。

### 电脑关机后的行为

这是运行在本机的 Streamlit 网站。只有电脑开机且后台进程正在运行时才能访问。
电脑关机后，本地网站必然停止。下次开机并重新打开已允许自动任务的 VS Code
项目时，网页会重新启动；也可以手动运行 `python scripts/start_web.py`。

如果希望电脑关机后网站仍能访问，需要后续部署到 Streamlit Community Cloud、
Render、Railway、VPS 或其他云服务器。当前版本只实现本地自动启动、自动重启
和访问地址显示。

### 网页运行故障排查

#### 为什么电脑关机后网页访问不了？

因为这是本地 Streamlit 网页，运行在你的电脑上。电脑关机后服务停止。想要
关机后也能访问，需要部署到云端。

#### 为什么打开了多个网页？

可能曾经手动运行过其他 Streamlit 项目。当前启动脚本会检查状态文件、PID、
端口和当前项目的绝对 `app.py` 路径，尽量避免重复启动本项目。

#### 为什么 `http://localhost:8501` 打不开？

- 确认已经运行 `python scripts/start_web.py`
- 确认已安装 Streamlit
- 确认在项目根目录运行
- 查看 `logs/streamlit_web.log`
- 运行 `python scripts/status_web.py`
- 检查启动输出是否因为端口占用而改用了 `8502` 或其他端口

#### 为什么端口 8501 被占用？

可能之前已有 Streamlit 或其他程序占用了端口。脚本不会结束未知程序，而会自动
尝试 `8502`、`8503`，并输出实际地址。

#### VS Code 打开项目后没有自动启动怎么办？

先确认工作区受信任并允许自动任务。仍未启动时手动执行：

```text
Ctrl + Shift + P
Tasks: Run Task
启动新闻知识库网页
```

也可以直接运行 `python scripts/start_web.py`。

## 个性化规则

初始偏好位于 `config/preferences.yaml`。当前版本使用简单、可解释的规则：

- 分类平均评分高于 `1` 时提高该分类权重
- 分类平均评分低于 `-1` 时降低该分类权重
- 高评分新闻中的关键词获得加分
- 低评分新闻中的关键词获得减分
- `值得追踪` 标签会加强相关主题
- `以后少推` 标签会降低相关主题
- 设置页保存的分类权重优先于 YAML 初始值

这不是复杂机器学习模型。它适合 MVP，容易理解，也便于后续调整。

## SQLite 数据

数据库包含：

- `reports`：日报正文、核心议题、文件路径、邮件状态和雷达统计
- `news_items`：代表新闻、规则/AI/最终分数、聚类、标签和背景补充
- `feedback`：评分、标签和笔记
- `user_preferences`：网页端手动设置的权重
- `news_interactions`：点赞、收藏、评论及其更新时间
- `user_settings`：邮件开关、发送时间、时区和本地自动发送开关
- `local_scheduler_runs`：本地调度器每日发送结果

同一天重复生成时会更新当天日报。旧新闻条目会标记为非当前版本，不会删除，
因此已经产生的点赞、收藏和评论仍可保留。

V4 会为 `news_items` 自动增量添加：`ai_score`、`ai_reason`、`ai_summary`、
`ai_tags`、`importance_tier`、`cluster_id`、`cluster_title` 和
`enrichment_json`。`reports` 会增加 `radar_stats_json`。迁移只使用
`ALTER TABLE` 补字段，不删除旧数据。

## RSS 与提示词

- RSS 来源：`config/sources.yaml`（旧版 `config/feeds.yaml` 仍可兼容）
- 初始偏好：`config/preferences.yaml`
- AI 评分提示词：`prompts/news_scoring_prompt.txt`
- 背景补充提示词：`prompts/news_enrichment_prompt.txt`
- 日报提示词：`prompts/daily_report_prompt.txt`
- 偏好总结提示词：`prompts/preference_summary_prompt.txt`

单个 RSS 来源失败不会阻断其他来源。所有来源都失败时，程序会明确报错，不会
生成没有来源的虚构日报。

## GitHub Actions

工作流位于 `.github/workflows/daily_news.yml`，负责每天运行：

```powershell
python -m src.main --send
```

需要在仓库的 `Settings -> Secrets and variables -> Actions` 中配置与 `.env`
对应的 Secrets。不要把密钥直接写进 YAML。

工作流会把生成的 `reports/*.md` 上传为保留 14 天的 artifact。

### 数据持久化限制

GitHub Actions 的运行环境是临时的：

1. 本地运行时，日报和评价保存在 `data/news_digest.db`；
2. GitHub Actions 默认负责每天发送邮件，开启 Pages 后也会提交 `docs/`；
3. Actions 中临时生成的 SQLite 数据库不会自动同步到本地网页端；
4. 若要让云端生成的日报进入同一个网页知识库，后续需要云数据库、对象存储，
   或把报告文件同步回仓库；
5. 当前版本仍不提交 SQLite 数据库，只提交启用后的静态日报归档。

## 安全说明

- `.env`、SQLite 数据库、生成的本地日报和 Streamlit secrets 均已忽略
- 代码不会打印 API Key 或 SMTP 授权码
- `.env.example` 只保留占位符
- 不抓取新闻全文
- 不创建虚假的新闻来源链接

## 常见问题

### DeepSeek 调用失败

程序会生成结构完整的 fallback 简报。检查 API Key、模型名、余额、网络和
`DEEPSEEK_BASE_URL`。

### 没有抓到新闻

检查网络与 `config/sources.yaml`，或临时增大：

```dotenv
NEWS_LOOKBACK_HOURS=72
```

### 网页端没有日报

先运行：

```powershell
python -m src.main --dry-run
```

### 邮件发送失败

确认邮箱已开启 SMTP、端口正确，并使用 SMTP 授权码。QQ 邮箱通常使用 SSL
端口 `465`。
