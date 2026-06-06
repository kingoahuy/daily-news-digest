# Daily News Digest

这是一个适合新手阅读和修改的每日热点新闻日报项目。程序每天从 RSS 获取财经、政治、社会、体育和科技/商业新闻，只使用 RSS 中的标题、摘要、发布时间、来源和链接，不抓取新闻全文。

程序会对新闻进行简单评分，选出一个核心议题，再通过 DeepSeek API 生成中文 Markdown 日报。日报保存在 `reports/`，也可以通过 SMTP 发送到邮箱。DeepSeek 调用失败时，程序会根据 RSS 数据自动生成简版 fallback 日报，不会因为大模型暂时不可用而直接崩溃。

## 工作流程

1. 读取 `config/feeds.yaml` 中的 RSS 地址。
2. 抓取最近一段时间的新闻并清理 HTML。
3. 按标题和链接去重。
4. 根据时效、分类和关键词为新闻评分。
5. 选择核心议题，并按分类保留高分新闻。
6. 调用 DeepSeek 生成中文日报；失败时生成 fallback 日报。
7. 保存 Markdown，转换为邮件 HTML。
8. 根据运行模式决定是否发送邮件。

## 申请 DeepSeek API Key

1. 打开 [DeepSeek 开放平台](https://platform.deepseek.com/)并注册或登录。
2. 在平台的 API Keys 页面创建一个新的 Key。
3. 妥善保存 Key。出于安全原因，平台通常不会再次完整显示它。
4. 确认账户有可用额度，并把 Key 填入本地 `.env` 的 `DEEPSEEK_API_KEY`。

API Key 不要写进 Python 文件，也不要提交到 GitHub。

## 准备邮箱 SMTP 授权码

邮件服务通常不允许程序直接使用网页登录密码，需要单独创建 SMTP 授权码。

以 QQ 邮箱为例：

1. 登录 QQ 邮箱网页版。
2. 打开设置中的账号、安全或第三方服务相关页面。
3. 开启 SMTP 服务。
4. 按页面提示生成授权码。
5. 在 `.env` 中填写邮箱地址和授权码：

```dotenv
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=your_email@qq.com
SMTP_PASSWORD=这里填写授权码，不是网页登录密码
MAIL_FROM=your_email@qq.com
MAIL_TO=receiver_email@qq.com
```

不同邮箱的 SMTP 主机、端口和授权方式可能不同，请以邮箱服务商当前说明为准。本项目默认使用 SSL 端口 `465`。

## 本地运行

先进入项目目录，然后创建虚拟环境。

Windows PowerShell：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Mac/Linux：

```bash
python -m venv .venv
source .venv/bin/activate
```

安装依赖：

```bash
pip install -r requirements.txt
```

## 配置 `.env`

Mac/Linux：

```bash
cp .env.example .env
```

Windows：

```powershell
copy .env.example .env
```

打开 `.env`，至少把下面的占位内容替换成真实 Key：

```dotenv
DEEPSEEK_API_KEY=your_deepseek_api_key
```

完整配置说明：

| 环境变量 | 用途 | 默认值 |
| --- | --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | 无，必填 |
| `DEEPSEEK_BASE_URL` | DeepSeek API 地址 | `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 模型名称 | `deepseek-v4-flash` |
| `SMTP_HOST` | SMTP 主机 | 发送邮件时必填 |
| `SMTP_PORT` | SMTP SSL 端口 | `465` |
| `SMTP_USER` | SMTP 登录账号 | 发送邮件时必填 |
| `SMTP_PASSWORD` | SMTP 授权码 | 发送邮件时必填 |
| `MAIL_FROM` | 发件人地址 | 发送邮件时必填 |
| `MAIL_TO` | 收件人地址，多个地址用英文逗号分隔 | 发送邮件时必填 |
| `TIMEZONE` | 日报日期使用的时区 | `Asia/Singapore` |
| `MAX_NEWS_PER_CATEGORY` | 每类最多保留条数 | `8` |
| `NEWS_LOOKBACK_HOURS` | 新闻回看小时数 | `36` |

## dry-run 测试

只生成文件，不发送邮件：

```bash
python -m src.main --dry-run
```

不带参数时也会默认使用 dry-run：

```bash
python -m src.main
```

如果 API Key 是无效占位值，DeepSeek 请求会失败，但程序仍会生成 fallback 日报。生成结果位于：

```text
reports/daily_news_YYYY-MM-DD.md
```

## 正式发送邮件

确认 DeepSeek 和 SMTP 配置都已填写后运行：

```bash
python -m src.main --send
```

成功时终端会显示“邮件发送成功”。失败时会提示检查 SMTP 主机、端口、账号和授权码，程序不会打印授权码本身。

## 配置 GitHub Secrets

把项目推送到 GitHub 后，进入仓库：

`Settings` -> `Secrets and variables` -> `Actions` -> `New repository secret`

建议添加以下 Secrets：

```text
DEEPSEEK_API_KEY
DEEPSEEK_BASE_URL
DEEPSEEK_MODEL
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASSWORD
MAIL_FROM
MAIL_TO
TIMEZONE
MAX_NEWS_PER_CATEGORY
NEWS_LOOKBACK_HOURS
```

其中 API Key 和 SMTP 信息必须填写。其余项目即使留空，程序也会使用 `.env.example` 中写明的默认值。

## GitHub Actions 自动运行

工作流文件位于 `.github/workflows/daily_news.yml`。它会：

- 使用 Python 3.11；
- 安装 `requirements.txt`；
- 运行 `python -m src.main --send`；
- 每天在 `Asia/Singapore` 时区 `08:13` 自动执行。

GitHub 的定时任务可能因平台繁忙而延迟几分钟，这不代表配置一定有问题。

## 手动触发 GitHub Actions

1. 打开 GitHub 仓库的 `Actions` 页面。
2. 在左侧选择 `Daily News Digest`。
3. 点击 `Run workflow`。
4. 选择分支，再次点击 `Run workflow`。
5. 打开本次运行记录查看每个步骤的日志。

## 添加或修改 RSS 来源

编辑 `config/feeds.yaml`。每个分类下面可以增加多个来源：

```yaml
technology:
  - name: Example Tech
    url: "https://example.com/rss.xml"
```

分类名会用于评分和日报分组。某个 RSS 源失效时，程序只打印警告并继续抓取其他来源。

## 常见错误排查

### 缺少 DeepSeek API Key

如果看到“缺少 DEEPSEEK_API_KEY”，请确认：

- 项目根目录存在 `.env`；
- 变量名拼写正确；
- 等号右侧不是空白；
- GitHub Actions 中已经创建同名 Secret。

### DeepSeek API 调用失败

程序会自动生成 fallback 日报。请检查 API Key、账户额度、模型名称、网络和 `DEEPSEEK_BASE_URL`。错误日志不会显示 API Key。

### 邮件发不出去

检查 SMTP 主机和端口是否属于你的邮箱服务商，确认邮箱已开启 SMTP 服务，并确认 `MAIL_FROM` 通常与 `SMTP_USER` 一致。

### SMTP 授权码错误

不要填写邮箱网页登录密码。重新生成授权码，更新 `.env` 或 GitHub Secret 后再运行。

### RSS 源失效

单个来源失败不会影响其他来源。根据终端警告找到来源，在浏览器中检查 RSS 地址，必要时修改或删除 `config/feeds.yaml` 中对应项。

### GitHub Actions 没运行

检查工作流文件是否已推送到默认分支、Actions 是否被仓库禁用、Secrets 是否齐全。定时工作流只会在默认分支上自动运行，并可能出现短暂延迟。

### 没有抓到新闻

检查网络和 RSS 地址，也可以临时增大：

```dotenv
NEWS_LOOKBACK_HOURS=72
```

如果所有 RSS 都不可用，程序会给出清晰错误，不会生成没有来源的虚构日报。

## 项目结构

```text
daily-news-digest/
├── src/                    # Python 程序
├── config/feeds.yaml       # RSS 来源
├── prompts/                # 大模型提示词
├── reports/                # 生成的 Markdown 日报
├── .github/workflows/      # GitHub Actions
├── requirements.txt
├── .env.example
├── README.md
└── .gitignore
```
