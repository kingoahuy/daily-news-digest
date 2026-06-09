# Daily News Digest

Daily News Digest 是一个本地运行的个人 AI 新闻雷达。它使用 Python 抓取 RSS，
调用 DeepSeek 执行评分、聚类、背景补充和日报生成，并通过 Next.js 提供现代化
网页界面。

## 唯一网页入口

日常使用只需要打开：

```text
http://localhost:3000
```

- `3000`：Next.js 主界面，也是唯一用户入口；
- `8000`：FastAPI 后端接口，不需要手动打开；
- `8501/8502`：旧 Streamlit 页面，不再默认启动。

旧的 `app.py` 保留为 legacy backup，不会被删除，也不会由开机自启或
`start_all.py` 启动。

## 主要功能

- RSS 多来源新闻抓取
- 本地规则评分与 DeepSeek AI 评分
- 新闻去重与主题聚类
- 核心新闻背景补充
- 中文或中英文双语日报
- SQLite 保存日报和新闻
- 点赞、取消点赞
- 收藏、取消收藏
- 评论与评论历史
- 我的收藏
- 互动偏好画像
- 邮件推送
- GitHub Actions 定时生成和发送
- GitHub Pages 静态日报归档

项目只使用 RSS 标题、摘要、来源、发布时间和链接，不抓取新闻全文。

## 快速开始

### 1. 安装 Python 依赖

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. 安装前端依赖

```powershell
cd web
npm install
cd ..
```

### 3. 配置环境变量

```powershell
Copy-Item .env.example .env
```

至少填写：

```dotenv
DEEPSEEK_API_KEY=your_deepseek_api_key
```

发送邮件还需要：

```dotenv
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=your_email_smtp_auth_code
MAIL_FROM=your_email@qq.com
MAIL_TO=receiver_email@qq.com
```

`SMTP_PASSWORD` 应填写 SMTP 授权码，不是邮箱网页登录密码。

### 4. 启动全部服务

```powershell
python scripts/start_all.py
```

它只启动：

1. FastAPI 后端；
2. Next.js 前端；
3. 本地邮件/日报调度器，前提是设置页已启用。

启动后打开：

```text
http://localhost:3000
```

### 5. 停止全部服务

```powershell
python scripts/stop_all.py
```

## 查看运行状态

Next.js：

```powershell
python scripts/status_frontend.py
```

FastAPI：

```powershell
python scripts/status_api.py
```

日志文件：

```text
logs/next_frontend.log
logs/api_backend.log
logs/windows_startup.log
```

状态文件：

```text
.runtime/frontend_status.json
.runtime/api_status.json
```

## 生成真实日报

只生成日报，不发送邮件：

```powershell
python -m src.main --dry-run
```

生成并发送邮件：

```powershell
python -m src.main --send
```

生成结果会写入：

```text
reports/daily_news_YYYY-MM-DD.md
data/news_digest.db
```

Next.js 首页会自动读取 SQLite 中最新日报。如果今天还没有日报，首页会明确提示
当前显示的是旧日期的历史日报，并提供“立即生成今日日报”按钮。刷新网页只会检查
状态和读取数据库，不会自动调用 DeepSeek；只有点击生成按钮或运行 `--dry-run`
时才会消耗 API。

## Next.js 页面

- `/`：最新真实日报、核心议题和分类新闻
- `/history`：历史日报中心，支持关键词、分类和日期筛选
- `/reports/{YYYY-MM-DD}`：指定日期日报、新闻互动和发送记录
- `/news/{id}`：AI 摘要、推荐理由、背景补充、点赞、收藏和评论
- `/analytics`：真实分类数量、重要新闻趋势和来源分布
- `/favorites`：SQLite 中已收藏的新闻
- `/profile`：点赞、收藏和评论形成的偏好画像
- `/settings`：真实运行设置，保存到 SQLite 并影响下一次 Python 生成或发送

首页和详情页不使用 mock 新闻。`web/src/data/mock-data.ts` 只保留为开发备用，
不会被活动页面导入。

## FastAPI 后端

后端默认地址：

```text
http://localhost:8000
```

如果 `8000` 被占用，会尝试 `8001`、`8002`。Next.js 会自动发现这三个本地端口。
也可以在前端构建环境中指定：

```dotenv
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

主要接口：

```text
GET  /api/health
GET  /api/reports
GET  /api/reports/latest
GET  /api/reports/today-status
POST /api/reports/generate-today
GET  /api/reports/by-date/{report_date}
GET  /api/reports/by-date/{report_date}/news
GET  /api/reports/{report_id}/news
POST /api/reports/{report_id}/send
GET  /api/reports/{report_id}/deliveries
GET  /api/news/{news_id}
GET  /api/news/{news_id}/interactions
POST /api/news/{news_id}/like
POST /api/news/{news_id}/favorite
GET  /api/news/{news_id}/comments
POST /api/news/{news_id}/comments
GET  /api/favorites
GET  /api/profile
GET  /api/analytics
GET  /api/settings
PUT  /api/settings
GET  /api/scheduler/status
POST /api/scheduler/check-once
```

API 直接复用 `src/database.py` 和 `src/preference.py`，不会建立第二套数据库。

## 网页设置页

打开：

```text
http://localhost:3000/settings
```

可以配置邮件开关、每日推送时间、省 API 模式、新闻总数、每类新闻数量、双语日报
和核心新闻背景补充。保存后写入 `data/news_digest.db` 的 `user_settings` 表，并在
下一次运行以下命令时生效：

```powershell
python -m src.main --dry-run
python -m src.main --send
```

关闭邮件开关后，`--send` 仍会生成并保存日报，但会跳过 SMTP 校验和邮件发送。
推送时间供本地邮件调度器读取；手动运行 `--send` 会立即执行。

本地自动发送需要同时满足：

1. 邮件推送已开启；
2. 本地自动发送已开启；
3. 电脑开机；
4. 项目服务或调度器进程正在运行；
5. SMTP 配置正确。

本地调度器不再要求当前时间精确等于计划时间。若计划 09:00 发送，默认会在
09:00 至 12:00 的 180 分钟宽限窗口内补发一次；当天已经成功发送过则不会重复
发送。超过宽限时间后会记录 `skipped`，并提示可以去历史日报中心手动发送。

每日推送时间只控制自动发送。需要发送某一天已经生成的日报时，请打开：

```text
http://localhost:3000/history
```

## 历史日报与指定日期发送

历史日报中心读取 SQLite `reports` 和 `news_items`，不会重新抓取 RSS，也不会重新
调用 DeepSeek。点击日期可查看完整 Markdown、当日新闻、互动状态和发送记录。

也可以使用命令行直接发送存量日报：

```powershell
python -m src.manual_sender --date 2026-06-07
python -m src.manual_sender --report-id 12
```

发送成功后会把 `reports.email_sent` 更新为已发送，并在 `email_deliveries` 表新增
一条 `manual` 记录。正常的 `python -m src.main --send` 会记录为 `scheduled`。
失败的尝试同样会保存状态和错误摘要，便于在历史详情页排查。

## 单独启动服务

FastAPI：

```powershell
python scripts/start_api.py
python scripts/status_api.py
python scripts/stop_api.py
```

Next.js：

```powershell
python scripts/start_frontend.py
python scripts/status_frontend.py
python scripts/stop_frontend.py
```

两个守护器都会监控子进程；服务意外退出时会尝试自动恢复。

启动全部本地服务和本地邮件调度器：

```powershell
python scripts/start_all.py
```

如果邮件推送和本地自动发送都已开启，终端会显示：

```text
本地邮件调度器 PID：xxxx
```

如果未启用，会显示类似：

```text
本地邮件调度器：未启用或未启动，原因：auto_send_local_enabled=false
```

单独启动调度器：

```powershell
python scripts/local_mail_scheduler.py
```

单独检查一次调度器状态：

```powershell
python scripts/local_mail_scheduler.py --once
```

输出会包含当前时间、计划时间、是否启用、当天是否已发送、是否准备发送，以及
跳过原因。日志路径：

```text
logs/local_mail_scheduler.log
```

## Windows 开机登录自启

本地网站在电脑关机期间无法访问。开机自启只能做到：下次登录 Windows 后自动恢复
FastAPI、Next.js 和本地调度器。

安装当前用户的登录自启：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_startup.ps1
```

安装后会创建 Windows 任务计划程序任务：

```text
DailyNewsDigestLocalServices
```

下次登录 Windows 后会自动执行：

```powershell
python scripts/start_all.py
```

启动日志写入：

```text
logs/windows_startup.log
```

安装后可立即手动启动一次：

```powershell
python scripts/start_all.py
```

检查服务是否恢复：

```powershell
python scripts/status_frontend.py
python scripts/status_api.py
```

移除自启：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/uninstall_startup.ps1
```

电脑关机后仍需访问时，需要部署到云服务器或使用 GitHub Pages 这类云端方案。

## VS Code 自动启动

`.vscode/tasks.json` 会在打开项目文件夹时运行：

```powershell
python scripts/start_all.py
```

第一次使用时，VS Code 可能要求允许工作区自动任务。

## 旧 Streamlit 页面

旧页面保留在 `app.py`，仅用于历史备份或临时调试。它不再是主入口，也不会默认
启动。如确实需要调试，可以手动运行：

```powershell
streamlit run app.py
```

日常使用不要打开 `8501/8502`，只使用 `http://localhost:3000`。

## 本地 07:30 自动生成与邮件调度

本地网页服务启动后，会同时尝试启动本地调度器：

```powershell
python scripts/start_all.py
```

本地调度器负责两件事：

1. 每天本地时间 `07:30` 检查今天是否已有日报；如果没有，就执行一次 `python -m src.main --dry-run`。
2. 如果设置页开启了“邮件发送”和“本地自动发送”，就在你设置的每日发送时间发送今天已经生成好的日报。

为避免浪费 DeepSeek API：

- 今天已经有日报时，不会重复自动生成。
- 网页刷新只检查状态，不会自动调用 DeepSeek。
- 自动生成失败后，会记录到 `logs/local_mail_scheduler.log` 和 SQLite，不会每分钟无限重试；你可以在首页点击“立即生成今日日报”手动处理。
- 自动邮件失败后，会记录失败原因；你可以在设置页点击“立即发送今天日报”手动处理。
- 同一天已经成功发送过邮件时，不会重复自动发送。

邮件设置规则：

- 关闭“邮件发送”：当天只生成日报，不发邮件。
- 开启“邮件发送”但关闭“本地自动发送”：`--send` 或手动按钮可以发，本地调度器不会自动发。
- 开启两者：到达你设置的时间后发送今天日报；如果今天日报还没生成，会先生成再发送。
- 默认补发宽限时间是 `180` 分钟，例如 09:00 发送可在 12:00 前补发一次。

本地调度器依赖本机运行：电脑关机、睡眠、网络断开、FastAPI/Next.js/调度器未启动时，都不会执行 07:30 生成或定时邮件。需要稳定每天自动生成和发送时，优先使用 GitHub Actions。

## GitHub Actions

`.github/workflows/daily_news.yml` 继续负责定时生成、邮件发送、日志上传和可选的
GitHub Pages 发布。本次 FastAPI 与 Next.js 本地接入不会改变 Actions 主流程。

需要在仓库的：

```text
Settings -> Secrets and variables -> Actions
```

配置：

```text
DEEPSEEK_API_KEY
SMTP_HOST
SMTP_USER
SMTP_PASSWORD
MAIL_FROM
MAIL_TO
```

### 本地定时邮件和 GitHub Actions 的区别

- 本地定时邮件：依赖你的电脑开机、项目服务运行、本地调度器进程运行，以及本机
  网络和 SMTP 配置；
- GitHub Actions：在 GitHub 云端定时运行，不依赖本机开机，也不需要本地网页
  保持打开；
- 如果你想稳定每天自动生成并发送，优先使用 GitHub Actions；
- 如果你希望电脑开机时也能本地补发，可开启网页设置页里的本地自动发送。

## GitHub Pages

手动生成并导出：

```powershell
python -m src.main --dry-run --export-pages
```

或单独更新静态归档：

```powershell
python -m src.pages_exporter
```

## 配置文件

- `config/app.yaml`：应用基础设置
- `config/sources.yaml`：RSS 来源
- `config/filtering.yaml`：评分阈值、时间窗口和分类权重
- `config/delivery.yaml`：邮件、Pages 和投递设置
- `config/preferences.yaml`：初始偏好

真实 API Key、邮箱和 SMTP 授权码只能保存在 `.env` 或 GitHub Secrets。

## 安全

以下内容不会提交到 Git：

- `.env` 和 `.env.*`
- `data/*.db`
- `logs/*.log`
- `.runtime/*`
- `web/node_modules`
- `web/.next`
- `.streamlit/secrets.toml`

程序不会主动打印 API Key 或 SMTP 授权码。

## 常见问题

### 页面提示后端未启动

运行：

```powershell
python scripts/start_all.py
```

再刷新 `http://localhost:3000`。

### 关机重启后网页打不开

本地网页不是云服务，关机后所有本地进程都会停止。重启后有两种处理方式：

1. 手动恢复：

```powershell
python scripts/start_all.py
```

2. 安装 Windows 登录自启：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_startup.ps1
```

安装后下次登录 Windows 会自动恢复服务。若仍打不开，先检查：

```powershell
python scripts/status_frontend.py
python scripts/status_api.py
```

再查看：

```text
logs/windows_startup.log
logs/next_frontend.log
logs/api_backend.log
```

### 页面提示还没有生成日报

网页只读取 SQLite 里已有的最新日报。如果当天还没有运行生成任务，就会显示昨天
或更早的日报。可以点击首页的“立即生成今日日报”，或运行：

```powershell
python -m src.main --dry-run
```

生成成功后，可以通过以下方式确认：

- 首页日期变成今天；
- 打开 `http://localhost:3000/history`，列表出现今天日期；
- 调用 `GET /api/reports/today-status`，确认 `has_today_report=true`。

### 设置了 9 点邮件但没有收到

本地调度器只有在电脑开机、项目服务运行、且调度器进程正在运行时才会发送。电脑
关机、网页没启动、调度器没启动，都会导致本地自动邮件不发送。

检查一次本地调度器：

```powershell
python scripts/local_mail_scheduler.py --once
```

推荐日常启动：

```powershell
python scripts/start_all.py
```

### 邮件发送失败

确认邮箱已开启 SMTP，并使用邮箱服务商生成的授权码。

### 点赞、收藏或评论刷新后消失

检查 FastAPI 是否运行，并确认 `data/news_digest.db` 可写。互动会直接保存到
SQLite，不保存在浏览器缓存。
