# 📬 AI Journal Workflow

> 基于 **Gmail API + Gemini AI** 的学术投稿自动化工作流系统

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Gmail API](https://img.shields.io/badge/Gmail-API%20v1-red.svg)](https://developers.google.com/gmail/api)
[![Gemini AI](https://img.shields.io/badge/Gemini-1.5%20Flash-orange.svg)](https://ai.google.dev)

---

## 📖 项目介绍

AI Journal Workflow 是一个专为文学/学术杂志编辑部设计的 **Gmail 投稿自动化工具**，解决了两个核心痛点：

1. **投稿整理繁琐**：手动从邮箱下载投稿附件、重命名归档，耗时且易出错
2. **反馈邮件重复**：每封评审反馈邮件格式相似却需逐一手写，效率低

本项目通过 Gmail API 自动检索、下载和归档投稿附件，再结合 **Gemini AI** 生成个性化评审反馈邮件，最终批量发送给作者。**评审、评语及通过/不通过意见均需人工完成，AI不直接参与审稿**

---

## ✨ 功能说明

### 📥 Sorter（投稿下载）
- 按日期范围搜索 Gmail 中的投稿邮件
- 支持关键词过滤（如"投稿"、"约稿"）
- 自动下载附件（支持 `.doc` `.docx` `.pdf` `.zip` `.txt`）
- 自动编号命名：`001 作品名.docx`、`002 作品名.pdf` ...
- 重名自动处理：`001 作品名(1).docx`

### 📤 Reviewer（评审反馈）
- 读取 Excel 评审表（支持多评委、多列重复列名）
- 在 Gmail 中自动搜索对应投稿邮件，提取发件人地址
- **Gemini AI** 生成温暖、专业的个性化评审反馈正文
- 无 Gemini Key 时自动回退到模板生成
- 通过稿件自动附加合同文件
- 发送记录持久化，避免重复发送

---

## 🛠️ 技术栈

| 技术 | 用途 |
|------|------|
| Python 3.10+ | 主要编程语言 |
| Gmail API v1 | 邮件读取与发送 |
| Google OAuth 2.0 | 身份认证 |
| Gemini 1.5 Flash | AI 邮件正文生成 |
| openpyxl + pandas | Excel 解析 |
| python-dotenv | 环境变量管理 |

---

## 📁 项目结构

```
AI-Journal-Workflow/
│
├── main.py                  # 统一 CLI 入口
├── requirements.txt         # 依赖清单
├── .env.example             # 环境变量模板（复制为 .env 后填写）
├── .gitignore               # Git 忽略规则
├── LICENSE                  # MIT License
│
├── sorter/                  # 投稿下载模块
│   ├── __init__.py
│   ├── gmail_client.py      # Gmail OAuth 认证与搜索
│   ├── downloader.py        # 附件下载与命名
│   ├── parser.py            # 邮件解析（正文、附件提取）
│   ├── utils.py             # 工具函数（路径、文件名处理）
│   └── workflow.py          # Sorter 主流程
│
├── reviewer/                # 评审反馈模块
│   ├── __init__.py
│   ├── excel_parser.py      # Excel 评审表解析
│   ├── gmail_service.py     # Gmail OAuth + 投稿邮件搜索
│   ├── ai_generator.py      # Gemini AI 邮件正文生成
│   ├── email_sender.py      # 邮件构建与发送
│   └── workflow.py          # Reviewer 主流程
│
├── downloads/               # 附件下载目录（已加入 .gitignore）
├── contracts/               # 合同文件目录
├── logs/                    # 运行日志目录（已加入 .gitignore）
└── docs/                    # 文档目录
```

---

## 🚀 安装步骤

### 1. 克隆项目

```bash
git clone https://github.com/your-username/AI-Journal-Workflow.git
cd AI-Journal-Workflow
```

### 2. 创建虚拟环境（推荐）

```bash
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

```bash
cp .env.example .env
# 然后编辑 .env，填入你的 API Key 和配置
```

---

## 🔑 Gmail API 配置

### 步骤一：创建 Google Cloud 项目

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目（或选择已有项目）

### 步骤二：启用 Gmail API

1. 左侧菜单 → **APIs & Services** → **Library**
2. 搜索 **Gmail API** → 点击 **Enable**

### 步骤三：创建 OAuth 凭证

1. 左侧菜单 → **APIs & Services** → **Credentials**
2. 点击 **Create Credentials** → **OAuth client ID**
3. Application type 选择 **Desktop app**
4. 下载 JSON 文件，重命名为 `credentials.json`
5. 将文件放置于项目根目录

### 步骤四：配置 OAuth 同意屏幕

1. **OAuth consent screen** → User Type 选 **External**
2. 填写应用名称
3. **Scopes** 中添加：
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.send`
4. **Test users** 中添加你的 Gmail 账号

> **首次运行**时会自动弹出浏览器完成授权，授权后生成 `token.json` 缓存，后续无需重复登录。

---

## 🤖 Gemini API 配置

1. 访问 [Google AI Studio](https://aistudio.google.com/app/apikey)
2. 点击 **Create API key** → 选择项目
3. 复制 API Key，填入 `.env` 文件：

```env
GEMINI_API_KEY=AIza...your_key_here
```

> Gemini API Key 可选。未配置时，系统自动使用内置模板生成邮件正文，功能不受影响。

---

## 📋 使用方法

### 运行投稿下载（Sorter）

```bash
# 下载本月所有带附件邮件
python main.py sorter

# 指定日期范围
python main.py sorter --start-date 2025-01-01 --end-date 2025-01-31

# 按关键词过滤
python main.py sorter --keywords 投稿,约稿,小说

# 自定义下载目录
python main.py sorter --download-dir /path/to/my/downloads

# 完整示例
python main.py sorter \
  --start-date 2025-01-01 \
  --end-date 2025-01-31 \
  --keywords 投稿,约稿 \
  --download-dir downloads
```

### 运行评审反馈（Reviewer）

```bash
# 配置好 reviews.xlsx 后直接运行
python main.py reviewer
```

### 查看帮助

```bash
python main.py --help
python main.py sorter --help
python main.py reviewer --help
```

---

## 📊 Workflow 示例

### Sorter 执行流程

```
[Gmail OAuth 认证]
        ↓
[构建搜索条件: after:2025/01/01 before:2025/02/01 has:attachment]
        ↓
[获取邮件列表（自动分页，最多500条/页）]
        ↓
[逐封解析邮件 → 关键词过滤]
        ↓
[提取作品名 → 清理文件名 → 下载附件]
        ↓
[001 黑夜航线.docx / 002 星际孤儿.pdf / ...]
```

### Reviewer 执行流程

```
[读取 reviews.xlsx]
        ↓
[解析评审信息：作品名、评语、最终意见]
        ↓
[Gmail 搜索：找到原始投稿邮件 → 提取发件人地址]
        ↓
[Gemini AI 生成个性化邮件正文（失败则用模板）]
        ↓
[通过稿：附合同发送 / 未过稿：发安慰信]
        ↓
[记录发送状态到 sent_log.json]
```

### Excel 评审表格式

| 作品编号 | 作品名称 | 评委1 | 意见 | 评语1 | 评委2 | 意见 | 评语2 | 评委3 | 意见 | 评语3 | 最终意见 |
|---------|---------|------|------|------|------|------|------|------|------|------|---------|
| 001 | 黑夜航线 | 张三 | 通过 | 文笔流畅... | 李四 | 通过 | 情节紧凑... | 王五 | 通过 | 人物鲜明... | 通过 |
| 002 | 星际孤儿 | 张三 | 不通过 | 结构松散... | 李四 | 通过 | 创意独特... | 王五 | 不通过 | 节奏偏慢... | 不通过 |

---

## ⚠️ 注意事项

- **`credentials.json` 和 `token.json` 已加入 `.gitignore`，切勿手动添加到版本控制**
- `reviews.xlsx` 含作者个人信息，也已加入 `.gitignore`，请勿上传
- `sent_log.json` 记录已发送状态，删除后将重新发送所有邮件
- Sorter 的 `downloads/` 目录可能含有版权作品，请注意保护
- Gmail API 每天有发送配额，大量发送时注意限制（免费账号约 500 封/天）
- 首次运行时需要浏览器 OAuth 授权，无法在无头服务器直接使用

---

## 🔧 日志查看

所有运行日志保存在 `logs/app.log`，同时输出到终端：

```bash
# 实时查看日志
tail -f logs/app.log
```

---

## 📈 正在进行的扩展方向

- [ ] 添加 Web UI（Flask/FastAPI）替代命令行
- [ ] 支持更多邮件服务（Outlook、QQ 邮箱）
- [ ] Gemini 提示词可配置化
- [ ] 添加单元测试
- [ ] Docker 容器化部署
- [ ] 定时任务（cron）自动运行

---

## 📄 License

本项目基于 [MIT License](LICENSE) 开源。
