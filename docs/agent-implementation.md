# 多用户加工智能体

Docker 启动：`docker compose up --build -d`。首次启动前在 `.env` 配置 `LASER_ADMIN_USERNAME` 与至少 12 字符的 `LASER_ADMIN_PASSWORD`；管理员登录后创建普通账号。HTTPS 部署设置 `LASER_COOKIE_SECURE=true`。

首页提供材料模板、质量目标与显式容差。公共原始记录共享，个人反馈与知识按服务端会话身份筛选。推荐返回一组：优先使用满足全部要求的历史实测案例，否则由训练集内分组验证选择模型。生成新参数需要明确设备步长，未定义步长的字段保持历史设置；不把已知不合格历史参数重新包装为模型推荐。

`/api/agent` 包含登录、用户、会话、单组推荐、反馈、知识和公式审核接口。接口文档见 `/docs`。旧 `/api/recommendations` 保留登录后的单组响应入口，旧全局反馈与可变 JSONL 数据管理接口已撤下，避免绕过用户隔离。原始数据仍可通过公共汇总接口查看。

反馈以 SQLite 追加事件为唯一写入来源，修正不会覆盖旧测量。删除、恢复改变当前数据投影；删除后 30 天不可再恢复，但事件保留。没有共享模型缓存，每次生成均从该用户的最新数据训练，响应附数据哈希、反馈版本与选模审计。并发修正使用事件版本检查。

旧 `feedback.jsonl` 和 `user_experiments.jsonl` 不再自动进入公共训练数据。管理员通过 `GET /api/agent/legacy-feedback` 查看，使用 `POST /api/agent/legacy-feedback/{id}/claim` 与 `{"username":"目标账号"}` 认领。旧文件不改写。

知识文件支持文本型 PDF、DOCX、Markdown、TXT。无法提取文字时明确失败。公共文献通过管理员导入接口载入 `docs/literature`，个人文献上传、检索、下载按账号授权。当前检索采用词项重叠，不依赖外部嵌入服务。LLM 的算法建议必须来自注册表，再由分组验证决定；任何文件均不能执行代码。公式提案只允许有来源、单位和适用材料的乘积／比值，管理员审核后才进入模型特征。

Provider 由管理中心的大语言模型页面配置，支持 Chat Completions 与 Ollama 协议。旧 YAML/环境配置仅在首次访问模型目录时兼容导入，之后以数据库为准。未启用或调用失败时仍可通过结构化表单使用免费本地推荐。

## 研究复现

运行 `docker compose run --rm --no-deps -v ${PWD}:/workspace -e PYTHONPATH=/workspace/apps/api api python /workspace/scripts/run_agent_experiment.py`。配置位于 `configs/agent_experiment.json`，输出位于 `data/processed/agent_experiment`。默认包含固定参数组留出、简单／复杂模型、机理类别消融、最近历史案例基线和开发集内反馈实验。完整选模记录、拆分清单、预测值与数据哈希一并保存。

## 验证

后端：`docker compose run --rm api pytest`。前端：`docker compose run --rm web npm run build`。测试采用临时账号与临时数据库；不改动实际反馈。现有历史研究分析测试与新智能体合同测试分别覆盖原研究函数和新用户隔离行为。

## 英文论文与复现命令

英文稿与原中文稿分开保存在 `docs/research/english/`，标题和文件名保持老师给定形式。Python 依赖固定在 `apps/api/requirements.lock.txt`，Docker 构建使用该约束文件。以下命令在仓库根目录的 PowerShell 执行：

```powershell
docker compose run --rm --no-deps -v "${PWD}:/workspace" -e PYTHONPATH=/workspace/apps/api -e LASER_EXPERIMENTS_DIR=/workspace/experiments/agent-research api python /workspace/scripts/run_agent_experiment.py
docker compose run --rm --no-deps -v "${PWD}:/workspace" -e PYTHONPATH=/workspace/apps/api -e LASER_EXPERIMENTS_DIR=/workspace/experiments/agent-research api python /workspace/scripts/agent_scoring_experiment.py
docker compose run --rm --no-deps -v "${PWD}:/workspace" -e PYTHONPATH=/workspace/apps/api -e LASER_EXPERIMENTS_DIR=/workspace/experiments/agent-research api python /workspace/scripts/validate_agent_experiment.py
./scripts/export_agent_paper.ps1
```

研究运行使用独立目录 `experiments/agent-research`，避免线上管理员批准的新增公式改变固定实验。该目录首次复现时应为空。验证脚本核对原始数据哈希、参数组划分、每种方法的测试记录、全部保存指标，以及开发集内部的反馈划分。该目录与线上运行时数据库均不进入 Git。

导出脚本保留单栏 DOCX，PDF 由独立 Docker 镜像中的 Pandoc 与 Typst 生成。期刊稿正文双栏、10 pt、栏距 5 mm，标题摘要关键词通栏；图 1/3/4 和三张表跨栏，图 2 单栏，矢量图按印刷尺寸绘制。现有单栏 PDF 位于 `english/archive`。DOCX 转换仍使用本机 Pandoc，页面检查使用 Poppler，不需要 Word 或本机 Python PATH。

仅重新导出双栏 PDF，可运行：

```powershell
docker compose run --rm --no-deps -v "${PWD}:/workspace" api python /workspace/scripts/build_journal_figures.py
docker compose --profile paper run --build --rm paper
```

`/api/agent/interpret` 仅提取用户明确描述的质量目标，返回草稿供表单核对，不触发参数推荐。管理员可在账号管理页提取公共文献中的乘积／比值关系、查看文献段落并审核；审核前不进入数值计算。尚未启用外部 Provider 时，目标表单、案例检索与确定性建模仍可运行；AI 解析和提案入口显示当前不可用状态。

反馈表单可记录与推荐不同的实际参数。在线修正界面、版本历史、回收站均按用户授权；管理员待认领区提供旧数据的明确归属操作。公式版本、各目标实际使用的中间量和选模结果保存在推荐记录中。没有共享模型文件缓存，各用户的数据视图每轮重新组装。

## 验收边界

固定测试集上的候选排序使用历史留出参数，不表示新开展的加工实验；默认在线候选还额外要求设备步长、完整预测目标及支持域检查。评分消融中的验证 RMSE 对单个响应模型的所有候选为同一常数，因此实验未把排序变化归功于该风险项。反馈实验是开发集内的顺序揭示与逐轮重训，不称为贝叶斯优化。

旧中文研究管线保留自己的 60/20/20 离线协议及冻结诊断，新英文研究采用独立 80/20 参数组划分。旧稿关于禁止生成参数执行及页面文字冻结的诊断不作为新版智能体验收规则；其数值、图表和文件一致性仍由原研究测试验证。
