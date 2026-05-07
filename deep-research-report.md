# 超快激光加工工艺决策智能体项目规划与技术路线研究报告

## 项目任务确认

从你给出的 PPT 可以直接提炼出，这个课程项目的真正目标并不是做一个“会聊天的 AI 壳子”，而是做一个围绕实验数据运行的工艺决策闭环原型：接收加工任务，检索相似历史数据，给出参数建议，再把实验结果反馈回系统做更新。对应的研究内容也已经很明确：先完成实验数据整理与统一建表，再完成相似案例检索与参数推荐，最后补上结果回写、迭代更新和界面展示。课程交付物同样清晰，包括原型程序或系统、数据整理与参数推荐说明、测试案例与结果分析、以及最终报告和汇报材料。

因此，项目边界应该尽早收紧到“工艺决策支持系统”而不是“全能制造智能体”。第一版只需要把超快激光加工里的核心决策链路打通，尤其是材料、关键激光参数与加工质量指标之间的关系建起来。更直白地说，首版系统的使命是**帮助人更快、更稳地做参数初选和迭代更新**，而不是替代实验人员做完全自动化控制。

## 核心问题分析

从已有研究看，超快激光加工本质上是一个高成本、强约束、黑箱味道很重的参数搜索问题。综述研究指出，超快激光可以覆盖金属、半导体和绝缘体等多类材料；但真正困难的部分在于参数空间往往很大，同时还要受高质量、低热影响、高吞吐等工艺限制共同约束。尤其在高平均功率和高通量场景下，热积累、表面粗糙度和几何精度之间会形成明显张力，单靠经验试错很难稳定找到满意解。citeturn6view1turn6view3

这也解释了你 PPT 里写到的“工艺窗口狭窄、数据获取难、需要多目标优化权衡”为什么不是表述性问题，而是系统设计问题。近年的综述和实验论文都在反复强调：传统试错往往耗时、昂贵，而且非线性的激光—材料相互作用会让结果高度敏感；相反，机器学习更适合承担过程监测、过程建模、质量预测、参数优化和自主路径规划这类任务。更关键的是，这类方法可以把“已有实验数据”和“新增实验反馈”组织成一个持续更新的闭环。citeturn17view0turn23view3

对你的项目来说，最重要的方法论不是“大模型本身有多强”，而是**先把目标函数和更新机制定义清楚**。针对激光工艺优化，研究已经明确指出，第一步必须先确认要优化的质量属性，再把这些属性组合成显式的代价函数或评价函数；而在实验预算有限、每次评估都昂贵的前提下，Bayesian optimization 特别适合做这种少样本、序贯式的参数搜索。相关研究显示，它既能在少量迭代内找到足够好的参数，也能比盲目搜索更高效地平衡探索和利用。citeturn23view0turn23view5turn23view6

把这些文献结论和你的课程要求合起来，本项目真正要解决的其实只有四件事：先把跨材料、跨实验批次的数据变成统一 schema；再把“质量好不好”转成机器可优化的目标；然后用尽可能少的实验次数做可解释的推荐；最后用一个能长期维护的应用外壳，把人机交互、结果展示和反馈写回组织起来。

## 目标与验收口径

我建议把目标拆成“必须达成”和“逐步增强”两层。必须达成的，是一个可运行的 MVP 闭环：用户输入材料、加工目标和约束；系统从历史数据中找相似案例；系统给出一组或多组可执行参数建议；实验完成后，用户把结果录入系统；系统能够把新结果纳入后续推荐。只要这条链路完整跑通，项目就已经成立。

验收口径也不宜一开始就追求“全自动最优”，而是要追求“结构化、可验证、能更新”。具体说，第一，数据层必须有统一字段定义，至少覆盖材料、工艺类型、关键激光参数、目标质量指标、实测结果和样本来源；第二，推荐层不能只返回一句自然语言建议，而要同时给出参数值、相似案例依据、预测结果和不确定性提示；第三，交互层需要能展示任务输入、案例检索、推荐参数和反馈录入四个页面状态；第四，反馈层必须保留实验日志，且新数据进入后能够影响下一轮推荐。之所以要保留原始质量指标而不是只保留一个总分，是因为文献反复强调激光优化首先要明确具体质量属性，而高斯过程回归之类的 surrogate model 又天然适合输出预测均值与不确定性，后续无论做单目标打分还是多目标扩展都会更稳。citeturn23view0turn23view2turn15view1turn15view2

就你这个课题的实际场景而言，首版最合理的验收方式不是去拼“全局最优”，而是看三件事：推荐是否比人工盲选更快收敛；推荐是否能给出足够清楚的理由；反馈写回之后推荐是否出现合理更新。只要这三点成立，你的系统就是一个合格的工艺决策原型，而不是一套静态展示页面。

## 技术路线与系统架构

我最推荐的技术路线不是“让大模型直接猜激光参数”，而是采用**检索 + surrogate model + 序贯优化 + LLM 解释**的四层架构。LLM 负责理解任务、组织工具调用、生成可读解释；真正决定数值参数的，是历史案例检索、回归建模和小步优化。这样做的好处是，LLM 的长处被用在自然语言理解和人机交互上，而最关键的科学计算部分仍然由可验证的数据模型承担。对于昂贵实验、少量样本、黑箱目标的优化任务，这也与自适应实验和 Bayesian optimization 的主流流程一致。citeturn23view5turn23view6turn17view0

```text
用户输入任务
  -> 任务解析与约束抽取
  -> 结构化过滤（材料 / 工艺 / 目标）
  -> 相似案例检索
  -> surrogate model 预测
  -> 候选参数生成与排序
  -> LLM 生成解释与交互文案
  -> 用户选择并执行实验
  -> 实验结果回写
  -> 模型与案例库更新
```

在云端主模型这一路，DeepSeek 目前已经提供兼容主流 chat-completions SDK 的接口，主模型是 `deepseek-v4-flash` 和 `deepseek-v4-pro`；但它的 `/chat/completions` 是显式 stateless 的，所以你的应用服务端必须自己保存消息历史，而不能把“多轮记忆”寄托在服务商端。官方文档还同时提供了 JSON Output、Tool Calls、Thinking/Non-Thinking 模式与 context caching；如果你要做 tool-calling agent，thinking 模式下凡是发生工具调用的轮次，都必须把 `reasoning_content` 连同消息一起带回后续请求，否则接口会报错。另一个非常实际的工程点是：旧别名 `deepseek-chat` 与 `deepseek-reasoner` 已被标记为将在 2026 年 7 月下旬退役，因此代码里不要再把这两个名字写死，应该从一开始就做 provider/model 抽象层。citeturn12view0turn12view4turn21view0turn21view1turn12view5

这也意味着，你的 LLM 输出契约最好一开始就走“强结构化”路线。DeepSeek 的 JSON Output 需要在接口参数里显式设置 `response_format={"type":"json_object"}`，同时在提示词里明确要求输出 json，并最好给出示例格式；否则官方文档已经提醒，模型可能出现长时间空白输出或因 token 截断而得到不完整结构。把这一层和后端的 schema 校验绑在一起，会比后期补救稳得多。若你后面确实要做工具调用，DeepSeek 还提供了 strict 模式用于按 JSON Schema 严格验证工具参数，这非常适合你这种“参数推荐必须可解析、可执行”的项目。citeturn24search0turn24search4turn24search7

在本地兜底这一路，Ollama 很适合承担“本地模型 fallback + 本地 embedding + 离线实验环境”的角色。它的本地 API 默认运行在 `http://localhost:11434/api`，提供 `/api/chat`、`/api/embed` 等接口，structured outputs 可直接用 JSON 或 JSON Schema 约束输出，而且返回里还带有 `total_duration`、`eval_count` 等性能指标，方便你顺手做一个简单的推理监控面板。另一方面，官方文档也明确说明，localhost 下默认不需要认证，因此你不应该把 11434 端口直接暴露给外网，而应该由你自己的后端服务做代理与权限控制。虽然它还提供了 OpenAI Responses API 兼容层，但该兼容层只支持 non-stateful flavor，所以对于这个项目，我更建议你在后端直接封装原生 `/api/chat` 和 `/api/embed`，少走一层兼容性弯路。citeturn13view0turn13view1turn13view2turn13view3turn13view4turn13view5turn13view6

如果你把这两条能力线统一成同一个内部接口，例如 `generate_structured()`、`chat_with_tools()`、`embed_texts()`、`list_models()`，那么上层业务根本不需要关心当前用的是 DeepSeek 还是 Ollama。这样一来，“云端主推理、本地兜底、训练数据不出内网、统一 JSON 契约”这四件事就能同时成立。

## 技术选型与语言决策

如果必须给出一个**主语言**，我建议选 **Python**。如果还要兼顾**美观、交互体验和长期可维护的 Web 前端**，则再加一层 **TypeScript**。换句话说，这不是“二选一”，而是“主语言选 Python，界面语言补 TypeScript”。

| 维度 | 推荐选择 |
|---|---|
| 主语言 | Python |
| 前端语言 | TypeScript |
| 后端框架 | FastAPI |
| 前端框架 | Next.js + React + shadcn/ui |
| 数据库存储 | SQLite 起步，预留 PostgreSQL 迁移 |
| 相似检索 | Faiss + 本地 embeddings |
| 建模与优化 | scikit-learn GPR 首版，Ax/BoTorch 二期升级 |
| 大模型接入 | DeepSeek 主用，Ollama 兜底 |

之所以把 Python 定为主语言，是因为你的项目核心工作——数据清洗、特征工程、相似案例检索、回归建模、Bayesian optimization、接口开发——都可以在同一条 Python 技术线上完成。FastAPI 适合作为后端骨架，因为它基于开放标准，能自动生成交互式 API 文档，并直接利用现代 Python 类型和 Pydantic 做输入输出验证。数据库部分，前期用 SQLite 很合适：FastAPI 官方教程直接把 SQLite 作为“单文件、Python 内置支持”的起步方案，同时也明确指出后续生产场景可以再迁移到 PostgreSQL 一类数据库服务器。citeturn14view6turn14view7turn11search15

界面层之所以建议 TypeScript + Next.js + React + shadcn/ui，是因为这套组合几乎正好打中你说的“兼顾美观与开发”。Next.js 的 App Router 原生建立在 React 的最新能力之上，支持 server/client component 分工；其官方文档还明确说明，服务端取数时数据库凭据与查询逻辑不会进入客户端 bundle，这对你这种要同时处理实验数据和模型接口的应用特别重要。React 的组件化思路则很适合把“任务表单、案例卡片、参数建议、反馈录入、实验记录”拆成稳定的界面单元。TypeScript 的静态类型检查可以把前后端契约尽量前置到编译期，而 shadcn/ui 的 open code、beautiful defaults 与 AI-ready 特性，又非常适合你把这份文档长期放在根目录，交给 Codex 继续接手开发和重构。citeturn14view0turn14view1turn14view2turn14view4turn14view5turn14view3

算法层面，我不建议你一上来就把复杂 agent 框架、复杂 MLOps 或大而全的 Bayesian optimization 平台全部拉进来。首版更稳的路径，是用 pandas/NumPy 完成数据处理，用 scikit-learn 的 GaussianProcessRegressor 做 small-data baseline，因为它能输出预测均值和标准差，天然适合“推荐参数 + 置信提示”这种场景。与此同时，scikit-learn 也提醒 Gaussian process 在高维空间会明显损失效率，所以你首版的特征一定要克制，不要把所有杂项字段都塞进去；先控制在材料、工艺类型、少量关键参数、目标指标和少量上下文变量上。相似案例检索可以先用 Faiss 作为本地 dense vector 搜索引擎；而如果后续真的进入多目标、约束优化或批量实验阶段，再升级到 Ax/BoTorch 会更合理。BoTorch 官方文档甚至明确把自己定位为更偏研究者和高级实践者的低层框架，并建议普通终端用户优先使用更高层的 Ax。citeturn15view1turn15view2turn15view4turn15view0turn23view5turn23view6

## 实施路径与仓库规范

实施上不要并行开十条线，而要坚持“先闭环，后增强”。第一阶段只做数据字典、字段统一、数据清洗和样本质量标注，把原始实验记录变成后续可建模的数据资产；第二阶段只做任务输入、相似案例检索和推荐结果展示，把前后端和模型网关打通；第三阶段再补 surrogate model，让系统从“相似案例参考”升级到“有数值预测和不确定性提示的推荐”；第四阶段才做反馈写回与小步 Bayesian optimization，让推荐结果能够随着新增实验自动变好。若时间充裕，再把显微图、粗糙度截图、孔径图像等质量测量接入视觉模块；已有相近研究表明，图像处理与深度学习结合可以显著减轻人工测量负担，并与参数优化循环衔接。citeturn23view4

下面这份目录结构，我认为已经足够适合作为你后续让 Codex 长期参考的项目根目录规范：

```text
project-root/
├─ README.md
├─ AGENTS.md
├─ docs/
│  ├─ PROJECT_PLAN.md
│  ├─ DATA_SCHEMA.md
│  ├─ OBJECTIVES.md
│  └─ API_CONTRACTS.md
├─ data/
│  ├─ raw/
│  ├─ interim/
│  └─ processed/
├─ apps/
│  ├─ api/
│  │  ├─ app/
│  │  │  ├─ main.py
│  │  │  ├─ routers/
│  │  │  ├─ schemas/
│  │  │  ├─ services/
│  │  │  ├─ providers/
│  │  │  ├─ retrieval/
│  │  │  ├─ surrogate/
│  │  │  └─ optimization/
│  └─ web/
│     ├─ app/
│     ├─ components/
│     ├─ lib/
│     └─ types/
├─ experiments/
│  ├─ runs/
│  └─ feedback_logs/
├─ tests/
├─ configs/
│  ├─ providers.yaml
│  ├─ objectives.yaml
│  └─ feature_flags.yaml
└─ notebooks/
```

其中 `AGENTS.md` 建议只写最硬的四条开发约束：**所有 LLM 输出必须过 schema 校验；所有参数推荐必须附相似案例依据和预测区间；所有实验反馈只能追加写入不能覆盖原记录；provider 切换必须通过配置完成而不是改业务逻辑。** 这样做的价值不在于“文档齐全”，而在于后续任何人类开发者或 Codex 接手时，都不会把系统又改回“聊天即推荐”的黑箱模式。

最终建议可以压缩成一句话：**用 Python 统一数据、建模、优化和 API，用 TypeScript/Next.js 把界面做漂亮；把 DeepSeek 放在任务解析、工具编排和结果解释的位置，把 Ollama 放在本地兜底、embedding 和离线运行的位置；把真正的数值推荐交给“相似案例检索 + surrogate model + 小步 Bayesian optimization”这条主链路。** 这条路线和你 PPT 中的项目闭环目标是一致的，也与当前官方 API 能力、少样本实验优化方法和课程项目可控工作量三者同时兼容。citeturn12view0turn21view0turn13view2turn13view3turn23view0turn23view5turn23view6