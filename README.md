# 玉石 AI 智能顾问

一个面向玉石行业的 AI 销售顾问 MVP。核心不是聊天，而是帮助消费者降低购买过程中的信息不对称：收集需求 → 图片/文字初步分析 → 风险解释 → 购买建议 → 人工咨询 → Lead。

## 已落地

- `web/`：消费者咨询网页、图片上传、真实 API 调用、人工咨询表单
- `backend/server.py`：Python 标准库 HTTP API、真实 OpenAI-compatible Chat Completions 调用、SQLite Lead/会话持久化、Admin API
- `web/admin.html`：轻量 Lead Dashboard
- `knowledge/jade/core.md`：玉石 AI 的第一性原理与安全边界
- `agent/agent.py`：保留原有跨境 Agent，不删除历史能力

## API

- `GET /api/health`
- `POST /api/chat`
- `POST /api/leads`
- `GET /api/admin/summary`
- `GET /api/admin/leads`

## 本地运行

Python 3.10+：

```bash
export AI_API_KEY="你的真实 API Key"
export AI_BASE_URL="https://api.openai.com/v1"
export AI_MODEL="gpt-4o-mini"
python start.py
```

然后打开 `http://localhost:8000`。

> API Key 只通过环境变量注入。不要写入代码或提交 GitHub。

## AI 产品边界

AI 只做基于用户文字和图片的初步分析，不确认真伪、天然/处理、产地或实验室检测结果，不保证升值，不虚构市场价格，也不替代专业鉴定证书。

## 下一步生产化

1. 接入正式对象存储/图片 CDN，而不是将图片长期存入数据库
2. 增加鉴权后的 Admin
3. 增加正式 PostgreSQL 与 Lead 状态管理
4. 增加结构化 AI 输出与评分
5. 增加自动化测试、日志、限流和部署配置
