# LLM Eval — 多模型横向评测框架

> 用同一套标准题，同时测 GPT-4o / Claude / 通义 / Kimi，自动生成对比报告。  
> 评分由 **LLM-as-a-Judge** 完成，结果可复现、可追溯。

![Python](https://img.shields.io/badge/Python-3.10+-3776ab?style=flat-square&logo=python)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)

---

## 为什么做这个

做 AI 产品需要对各家模型的能力有量化认知，不能只靠「感觉谁更好」。  
这个工具的目标：**把模型对比从定性观察变成可量化的数据**。

设计原则：
- **场景驱动**：题目贴近真实产品场景，而非学术 benchmark
- **自动评分**：LLM-as-a-Judge 打分，减少人工评测成本
- **可扩展**：加新模型只需在 `config.yaml` 加一行，加新题只需写 YAML

---

## 评测场景（15 题 × 5 类）

| 类别 | 题目数 | 测试重点 |
|---|---|---|
| **写作能力** | 3 | 商业邮件、产品文案、风格改写 |
| **推理能力** | 3 | 逻辑推导、商业数学、情境决策 |
| **指令遵循** | 3 | 严格格式输出、多约束写作、结构化提取 |
| **中文理解** | 3 | 语境歧义、古诗词应用、写作风格辨析 |
| **代码能力** | 3 | 算法实现、Bug 定位修复、Code Review |

> 题目设计原则：有明确的正误标准（方便 Judge 打分），同时覆盖 AI 产品的真实使用场景。

---

## 快速开始

```bash
git clone https://github.com/G3-58/llm-eval.git
cd llm-eval
pip install -r requirements.txt

cp .env.example .env
# 填入你有的 API Key，没有的留空会自动跳过

# 跑全部场景
python main.py

# 只跑写作 + 推理
python main.py --categories writing reasoning

# 只收集回答，不评分（省 Judge API 费用）
python main.py --no-judge

# 从已有原始结果重新生成报告
python main.py --report-only results/scores_xxx.json
```

---

## 报告示例

**→ [查看完整示例报告](results/sample_report.md)**（GPT-4o / Claude / 通义 / Kimi 四模型横评，15题全量结果）

```
══════════════════════════════════════════════════════════════
  RESULTS SUMMARY
══════════════════════════════════════════════════════════════
  1. Claude 3.5 Sonnet               83.1  █████████████████
  2. GPT-4o                          79.8  ███████████████░░
  3. 通义千问 Plus                    73.5  ██████████████░░░
  4. Kimi (moonshot-v1-8k)           69.2  █████████████░░░░
══════════════════════════════════════════════════════════════

  Full report → results/report_20250315_143200.md
```

**关键发现**（示例报告摘要）：
- **指令遵循**差异最大：Claude 在严格格式约束下错误率最低；GPT-4o 有"输出前加说明"的习惯；Kimi 在全角/半角符号上容易出错
- **中文理解**上通义千问反超 GPT-4o：职场语境、言外之意的把握明显更准
- **推理**是 GPT-4o 的相对优势：逆否推导、多步数学题上最稳定

Markdown 报告包含：
- 总分排行榜
- 各类别能力热力图
- 逐题对比表（综合分 / 优点 / 问题 / 响应时间）
- 最佳回答展示（可折叠）
- 综合洞察（每个模型的强项 / 弱项）

---

## 架构

```
llm-eval/
├── prompts/              # 评测题库（YAML，易于扩展）
│   ├── writing.yaml
│   ├── reasoning.yaml
│   ├── instruction.yaml
│   ├── chinese.yaml
│   └── coding.yaml
├── models/               # 模型 Adapter（统一接口）
│   ├── base.py           # ModelAdapter 抽象类
│   ├── openai_model.py   # GPT-4o
│   ├── anthropic_model.py# Claude
│   ├── dashscope_model.py# 通义千问（OpenAI 兼容端点）
│   └── moonshot_model.py # Kimi（OpenAI 兼容端点）
├── runner.py             # 并发调用所有模型
├── judge.py              # LLM-as-a-Judge 评分
├── report.py             # Markdown 报告生成
├── main.py               # CLI 入口
└── config.yaml           # 模型 & 运行配置
```

---

## 扩展指南

**加新模型**：在 `config.yaml` 的 `models:` 下添加一条，如果是 OpenAI-compatible API 直接用 `dashscope_model.py` 的模式复制一份即可。

**加新题目**：在对应的 `prompts/*.yaml` 文件里追加一条，填写 `prompt` 和 `eval_criteria` 即可，无需改代码。

**换 Judge 模型**：修改 `config.yaml` 里的 `judge.provider` 和 `judge.model`。

---

## 局限性说明

- LLM-as-a-Judge 本身存在偏见（倾向于更长的回答、与自身风格相似的回答）
- 15 道题不能代表模型的全部能力，采样结果存在方差
- 部分题目（尤其推理类）有客观标准答案，但 Judge 打分仍可能有偏差

---

*本项目是 [ai-product-teardown](https://github.com/G3-58/ai-product-teardown) 的配套工具——把产品拆解里的定性观察，用数据验证一遍。*
