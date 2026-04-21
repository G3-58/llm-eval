"""
Generate a structured Markdown benchmark report from judge scores.
"""
from collections import defaultdict
from datetime import datetime


def _avg(lst: list) -> float:
    return round(sum(lst) / len(lst), 1) if lst else 0.0


def generate(scores: list[dict], output_path: str):
    """Write a Markdown report to output_path."""

    # ── Aggregate ──────────────────────────────────────────────────────────────
    models = sorted({s["model_name"] for s in scores})
    categories = sorted({s["category"] for s in scores}, key=lambda c: {
        "writing": 1, "reasoning": 2, "instruction": 3, "chinese": 4, "coding": 5
    }.get(c, 9))
    cat_names  = {s["category"]: s["category_name"] for s in scores}

    # model → category → [overall scores]
    model_cat: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    # model → [all overall scores]
    model_all: dict[str, list] = defaultdict(list)
    # prompt_id → model → score record
    prompt_model: dict[str, dict[str, dict]] = defaultdict(dict)

    for s in scores:
        if s.get("skipped"):
            continue
        model_cat[s["model_name"]][s["category"]].append(s["overall"])
        model_all[s["model_name"]].append(s["overall"])
        prompt_model[s["prompt_id"]][s["model_name"]] = s

    # ── Report ─────────────────────────────────────────────────────────────────
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines += [
        f"# LLM Benchmark Report",
        f"",
        f"> 生成时间：{now}  ",
        f"> 评测模型：{' / '.join(models)}  ",
        f"> 评测场景：{len({s['prompt_id'] for s in scores})} 题 × {len(categories)} 类别",
        f"",
    ]

    # ── 总分排行 ────────────────────────────────────────────────────────────────
    lines += ["## 总分排行", ""]
    header = "| 排名 | 模型 | 总分 | " + " | ".join(cat_names[c] for c in categories) + " |"
    sep    = "|---" * (3 + len(categories)) + "|"
    lines += [header, sep]

    ranking = sorted(models, key=lambda m: _avg(model_all[m]), reverse=True)
    for rank, m in enumerate(ranking, 1):
        total = _avg(model_all[m])
        cat_scores = " | ".join(str(_avg(model_cat[m][c])) for c in categories)
        lines.append(f"| {rank} | **{m}** | **{total}** | {cat_scores} |")
    lines.append("")

    # ── 分类得分热力图（文字版）──────────────────────────────────────────────────
    lines += ["## 分类能力对比", ""]
    for cat in categories:
        lines.append(f"### {cat_names[cat]}")
        lines.append("")
        cat_scores_sorted = sorted(
            [(m, _avg(model_cat[m][cat])) for m in models],
            key=lambda x: -x[1],
        )
        for m, score in cat_scores_sorted:
            bar = "█" * int(score / 5) + "░" * (20 - int(score / 5))
            lines.append(f"- **{m}** `{score:5.1f}` {bar}")
        lines.append("")

    # ── 逐题详情 ────────────────────────────────────────────────────────────────
    lines += ["## 逐题详情", ""]
    prompt_ids_ordered = sorted(
        prompt_model.keys(),
        key=lambda pid: (pid[0], pid),
    )
    for pid in prompt_ids_ordered:
        model_scores = prompt_model[pid]
        if not model_scores:
            continue
        sample = next(iter(model_scores.values()))
        lines += [
            f"### [{pid}] {sample['prompt_name']}（{sample['category_name']}）",
            "",
        ]
        # Score table
        header2 = "| 模型 | 综合分 | 优点 | 问题 | 响应时间 |"
        sep2    = "|---|---|---|---|---|"
        lines  += [header2, sep2]
        for m in ranking:
            rec = model_scores.get(m)
            if not rec:
                lines.append(f"| {m} | — | — | — | — |")
                continue
            lines.append(
                f"| {m} | **{rec['overall']}** | {rec['strength']} "
                f"| {rec['weakness']} | {rec['latency_ms']}ms |"
            )
        lines.append("")

        # Show best response
        best_m = max(model_scores, key=lambda m: model_scores[m]["overall"])
        best_rec = model_scores[best_m]
        lines += [
            f"<details>",
            f"<summary>最佳回答：{best_m}（{best_rec['overall']}分）</summary>",
            "",
            "```",
            best_rec["response"][:1200] + ("..." if len(best_rec["response"]) > 1200 else ""),
            "```",
            "",
            "</details>",
            "",
        ]

    # ── 综合洞察 ────────────────────────────────────────────────────────────────
    lines += ["## 综合洞察", ""]
    for m in ranking:
        cat_best  = max(categories, key=lambda c: _avg(model_cat[m][c]))
        cat_worst = min(categories, key=lambda c: _avg(model_cat[m][c]))
        lines += [
            f"**{m}**",
            f"- 综合得分：{_avg(model_all[m])} / 100",
            f"- 最强维度：{cat_names[cat_best]}（{_avg(model_cat[m][cat_best])}分）",
            f"- 最弱维度：{cat_names[cat_worst]}（{_avg(model_cat[m][cat_worst])}分）",
            "",
        ]

    lines += [
        "---",
        "",
        "*本报告由 [llm-eval](https://github.com/G3-58/llm-eval) 自动生成。"
        "评分由 LLM-as-a-Judge 完成，存在主观性，仅供参考。*",
    ]

    Path_out = output_path
    with open(Path_out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n[Report] Saved to {Path_out}")
