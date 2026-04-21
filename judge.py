"""
LLM-as-a-Judge: scores each model response against the prompt's eval_criteria.
Returns structured scores (per criterion + overall) and brief feedback.
"""
import asyncio
import json
import re
from models.base import ModelResponse

JUDGE_PROMPT = """\
你是一位严格公正的 AI 能力评测专家。请对下面的 AI 模型回答进行评分。

【测试题目】
{prompt}

【评分标准】
{criteria}

【模型回答】
{response}

评分说明：
- 逐条对照评分标准打分，每条标准 0~5 分（0=完全未满足，3=部分满足，5=完全满足）
- 给出一个综合分 overall（0~100）
- 用 1-2 句话说明最突出的优点和最主要的问题

只输出 JSON，格式如下（不要有任何其他内容）：
{{
  "criteria_scores": {{"标准描述1": 分数, "标准描述2": 分数, ...}},
  "overall": 综合分,
  "strength": "最突出的优点",
  "weakness": "最主要的问题"
}}
"""


async def judge_one(
    response: ModelResponse,
    prompt_cfg: dict,
    judge_client,
    judge_model: str,
) -> dict:
    """Score a single ModelResponse. Returns a dict with scores."""
    if response.error:
        return {
            "model_id":       response.model_id,
            "model_name":     response.model_name,
            "prompt_id":      response.prompt_id,
            "overall":        0,
            "criteria_scores": {},
            "strength":       "N/A",
            "weakness":       f"模型出错: {response.error}",
            "latency_ms":     response.latency_ms,
            "skipped":        True,
        }

    criteria = prompt_cfg.get("eval_criteria", [])
    criteria_text = "\n".join(f"- {c}" for c in criteria)

    judge_input = JUDGE_PROMPT.format(
        prompt=prompt_cfg["prompt"],
        criteria=criteria_text,
        response=response.content,
    )

    try:
        resp = await judge_client.chat.completions.create(
            model=judge_model,
            temperature=0.1,
            messages=[{"role": "user", "content": judge_input}],
        )
        raw = resp.choices[0].message.content.strip()
        # Strip markdown code fences if present
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        parsed = json.loads(raw)
    except Exception as e:
        parsed = {
            "criteria_scores": {},
            "overall": -1,
            "strength": "",
            "weakness": f"Judge parse error: {e}",
        }

    return {
        "model_id":       response.model_id,
        "model_name":     response.model_name,
        "prompt_id":      response.prompt_id,
        "category":       prompt_cfg["category"],
        "category_name":  prompt_cfg["category_name"],
        "prompt_name":    prompt_cfg["name"],
        "overall":        parsed.get("overall", 0),
        "criteria_scores": parsed.get("criteria_scores", {}),
        "strength":       parsed.get("strength", ""),
        "weakness":       parsed.get("weakness", ""),
        "latency_ms":     response.latency_ms,
        "response":       response.content,
    }


async def judge_all(
    responses: list[ModelResponse],
    prompts_by_id: dict,
    judge_cfg: dict,
) -> list[dict]:
    """Judge all responses, return list of scored dicts."""
    import os
    from openai import AsyncOpenAI

    # Try primary judge provider
    provider = judge_cfg.get("provider", "openai")
    model    = judge_cfg.get("model", "gpt-4o")

    if provider == "openai" and os.getenv("OPENAI_API_KEY"):
        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    elif provider == "dashscope" and os.getenv("DASHSCOPE_API_KEY"):
        client = AsyncOpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
    else:
        # Fallback
        fb_provider = judge_cfg.get("fallback_provider", "dashscope")
        model = judge_cfg.get("fallback_model", "qwen-plus")
        if fb_provider == "dashscope" and os.getenv("DASHSCOPE_API_KEY"):
            client = AsyncOpenAI(
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )
        else:
            print("[Judge] No judge API key found — skipping scoring.")
            return []

    print(f"\n[Judge] Scoring {len(responses)} responses with {model}...")
    semaphore = asyncio.Semaphore(3)

    async def bounded(resp):
        async with semaphore:
            p_cfg = prompts_by_id.get(resp.prompt_id, {})
            result = await judge_one(resp, p_cfg, client, model)
            print(f"  ✓ Judged: {resp.model_name} × {resp.prompt_id} → {result['overall']}/100")
            return result

    return await asyncio.gather(*[bounded(r) for r in responses])
