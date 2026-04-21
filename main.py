"""
LLM Eval — CLI Entry Point
===========================
Usage:
  python main.py                          # 跑所有场景
  python main.py --categories writing reasoning   # 只跑指定场景
  python main.py --no-judge              # 只收集回答，不评分
  python main.py --report-only results/run_xxx.json  # 只生成报告
"""
import asyncio
import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config(path: str = "config.yaml") -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def print_banner(models, prompts, categories):
    print("\n" + "═" * 60)
    print("  LLM Benchmark Eval")
    print("═" * 60)
    print(f"  Models   : {', '.join(m.name for m in models)}")
    print(f"  Prompts  : {len(prompts)} 题")
    print(f"  Categories: {', '.join(categories or ['all'])}")
    print("═" * 60 + "\n")


async def main():
    parser = argparse.ArgumentParser(description="LLM Eval Tool")
    parser.add_argument("--categories", nargs="*",
                        choices=["writing", "reasoning", "instruction", "chinese", "coding"],
                        help="只评测指定类别（默认全部）")
    parser.add_argument("--no-judge", action="store_true",
                        help="跳过 LLM-as-a-Judge 评分，只收集模型回答")
    parser.add_argument("--report-only", type=str, metavar="JSON",
                        help="跳过推理，直接从已有 JSON 生成报告")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--output-dir", default="results")
    args = parser.parse_args()

    cfg = load_config(args.config)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # ── Report-only mode ─────────────────────────────────────────────────────
    if args.report_only:
        scores = json.loads(Path(args.report_only).read_text(encoding="utf-8"))
        import report as rpt
        rpt.generate(scores, str(out_dir / f"report_{run_id}.md"))
        return

    # ── Build models ─────────────────────────────────────────────────────────
    from models import build_models
    print("[Models] Checking available models...")
    models = build_models(cfg["models"])
    if not models:
        print("No models available. Please set at least one API key in .env")
        return

    # ── Load prompts ─────────────────────────────────────────────────────────
    from runner import load_prompts, run_all
    all_prompts = load_prompts("prompts")
    prompts = [p for p in all_prompts if not args.categories or p["category"] in args.categories]
    prompts_by_id = {p["id"]: p for p in all_prompts}

    print_banner(models, prompts, args.categories)

    # ── Run models ────────────────────────────────────────────────────────────
    print("[Runner] Sending prompts to all models...")
    run_cfg = cfg.get("runner", {})
    responses = await run_all(
        models=models,
        prompts=prompts,
        max_concurrency=run_cfg.get("max_concurrency", 4),
        timeout=run_cfg.get("timeout_seconds", 60),
    )

    # Save raw responses
    raw_path = out_dir / f"raw_{run_id}.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(
            [{"model_id": r.model_id, "model_name": r.model_name,
              "prompt_id": r.prompt_id, "content": r.content,
              "latency_ms": r.latency_ms, "error": r.error}
             for r in responses],
            f, ensure_ascii=False, indent=2,
        )
    print(f"\n[Runner] Raw responses saved → {raw_path}")

    if args.no_judge:
        print("[Judge] Skipped (--no-judge)")
        return

    # ── Judge ─────────────────────────────────────────────────────────────────
    from judge import judge_all
    scores = await judge_all(responses, prompts_by_id, cfg.get("judge", {}))
    if not scores:
        print("[Judge] No scores generated.")
        return

    scores_path = out_dir / f"scores_{run_id}.json"
    with open(scores_path, "w", encoding="utf-8") as f:
        json.dump(scores, f, ensure_ascii=False, indent=2)
    print(f"[Judge] Scores saved → {scores_path}")

    # ── Report ────────────────────────────────────────────────────────────────
    import report as rpt
    report_path = out_dir / f"report_{run_id}.md"
    rpt.generate(scores, str(report_path))

    # ── Summary ───────────────────────────────────────────────────────────────
    from collections import defaultdict
    model_totals: dict[str, list] = defaultdict(list)
    for s in scores:
        if not s.get("skipped"):
            model_totals[s["model_name"]].append(s["overall"])

    print("\n" + "═" * 60)
    print("  RESULTS SUMMARY")
    print("═" * 60)
    ranking = sorted(model_totals.items(), key=lambda x: -sum(x[1]) / len(x[1]))
    for rank, (name, all_scores) in enumerate(ranking, 1):
        avg = round(sum(all_scores) / len(all_scores), 1)
        bar = "█" * int(avg / 5)
        print(f"  {rank}. {name:30s} {avg:5.1f}  {bar}")
    print("═" * 60)
    print(f"\n  Full report → {report_path}\n")


if __name__ == "__main__":
    asyncio.run(main())
