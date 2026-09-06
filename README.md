# 超快激光加工工艺数据库智能体

本项目是面向超快激光加工实验数据的工艺决策 MVP。系统围绕“任务输入、相似案例检索、参数推荐、实验反馈写回”建立闭环，用数据模型承担数值推荐，用界面和可选 LLM provider 承担交互解释。

当前多用户智能体的登录、账号管理、模型配置、Credit 和迁移说明见 [管理与部署](docs/admin-credit-deployment.md)，产品实现见 [实现说明](docs/agent-implementation.md)。正式环境为 `server-shu`，功能分支经 PR 审阅并合入 `main` 后再自动更新。

## 功能

- 读取 `data/raw/` 下的多材料 Excel 原始实验数据。
- 统一材料、激光参数和加工质量指标字段。
- 按材料、目标深度、目标直径、粗糙度约束和参数约束检索相似案例。
- 返回推荐参数、预测质量、相似案例和可读解释。
- 按账号向 SQLite 追加反馈事件，支持修正、删除与 30 天恢复；旧 JSONL 需管理员认领。
- 提供 FastAPI 后端和 Next.js 前端工作台。

## 快速启动

优先使用 Docker：

```powershell
docker compose up --build
```

PyCharm 中可以直接使用右上角 Run widget 选择：

- `Docker Compose Up`：执行 `scripts/compose-up.ps1`，等价于在项目根目录运行 `docker compose up -d --build`。
- `Docker Compose Down`：执行 `scripts/compose-down.ps1`，等价于在项目根目录运行 `docker compose down`。

如果本机 8000 或 3000 端口已被占用，可以覆盖端口：

```powershell
$env:API_PORT='18000'; $env:WEB_PORT='13000'; docker compose up --build
```

服务地址：

- Web: http://localhost:3000
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

本地后端开发：

```powershell
cd apps/api
uv sync --dev
uv run uvicorn app.main:app --reload
```

本地前端开发：

```powershell
cd apps/web
npm install
npm run dev
```

## 目录

```text
apps/api        FastAPI 后端、数据清洗、推荐与反馈服务
apps/web        Next.js 前端工艺决策工作台
configs         provider、目标函数和功能开关配置
data/raw        原始 Excel 数据
data/interim    中间数据，默认不提交
data/processed 处理后数据，默认不提交
docs            项目计划、数据 schema 和 API 契约
experiments     运行记录与反馈日志，默认不提交运行产物
tests           跨模块测试占位
```

## Git

远端仓库：

```text
git@gitee.com:SHU-SPE-Sandrone/ultrafast_laser_process_decision_agent.git
```

