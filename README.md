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
2. Next.js 前端。

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

Next.js 首页会自动读取 SQLite 中最新日报。如果还没有日报，页面会提示先运行
`python -m src.main --dry-run`。

## Next.js 页面

- `/`：最新真实日报、核心议题和分类新闻
- `/news/{id}`：AI 摘要、推荐理由、背景补充、点赞、收藏和评论
- `/analytics`：真实分类数量、重要新闻趋势和来源分布
- `/favorites`：SQLite 中已收藏的新闻
- `/profile`：点赞、收藏和评论形成的偏好画像
- `/settings`：阅读偏好界面；当前不会修改 Python 邮件和生成配置

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
GET  /api/reports/latest
GET  /api/reports/{report_id}/news
GET  /api/news/{news_id}
GET  /api/news/{news_id}/interactions
POST /api/news/{news_id}/like
POST /api/news/{news_id}/favorite
GET  /api/news/{news_id}/comments
POST /api/news/{news_id}/comments
GET  /api/favorites
GET  /api/profile
GET  /api/analytics
```

API 直接复用 `src/database.py` 和 `src/preference.py`，不会建立第二套数据库。

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

## Windows 开机登录自启

安装当前用户的登录自启：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_startup.ps1
```

下次登录 Windows 后会自动启动 FastAPI 和 Next.js。

移除自启：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/uninstall_startup.ps1
```

本地网站在电脑关机期间无法访问；开机自启表示下次登录 Windows 后自动恢复。
电脑关机后仍需访问时，需要部署到云服务器。

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

### 页面提示还没有生成日报

运行：

```powershell
python -m src.main --dry-run
```

### 邮件发送失败

确认邮箱已开启 SMTP，并使用邮箱服务商生成的授权码。

### 点赞、收藏或评论刷新后消失

检查 FastAPI 是否运行，并确认 `data/news_digest.db` 可写。互动会直接保存到
SQLite，正常情况下刷新页面后仍会保留。
