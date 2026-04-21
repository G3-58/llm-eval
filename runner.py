"""
Parallel runner — sends every prompt to every available model concurrently.
"""
import asyncio
from pathlib import Path
import yaml
from models.base import ModelResponse


def load_prompts(prompts_dir: str = "prompts") -> list[dict]:
    """Load all YAML prompt files, return flat list of prompt dicts."""
    all_prompts = []
    for path in sorted(Path(prompts_dir).glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        for p in data["prompts"]:
            p["category"]     = data["category"]
            p["category_name"] = data["name"]
        all_prompts.extend(data["prompts"])
    return all_prompts


async def _run_one(model, prompt_text: str, prompt_id: str, timeout: int) -> ModelResponse:
    try:
        return await asyncio.wait_for(
            model.generate(prompt_text, prompt_id),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        from models.base import ModelResponse
        return ModelResponse(
            model_id=model.id, model_name=model.name, prompt_id=prompt_id,
            content="", latency_ms=timeout * 1000, error="Timeout",
        )


async def run_all(
    models: list,
    prompts: list[dict],
    max_concurrency: int = 4,
    timeout: int = 60,
    categories: list[str] | None = None,
) -> list[ModelResponse]:
    """
    Run all (model, prompt) pairs, respecting max_concurrency.
    Returns flat list of ModelResponse objects.
    """
    if categories:
        prompts = [p for p in prompts if p["category"] in categories]

    semaphore = asyncio.Semaphore(max_concurrency)

    async def bounded(model, prompt):
        async with semaphore:
            label = f"{model.name} × {prompt['id']}"
            print(f"  ▶ {label}")
            result = await _run_one(model, prompt["prompt"], prompt["id"], timeout)
            status = "✓" if not result.error else f"✗ {result.error}"
            print(f"  {status} {label} ({result.latency_ms}ms)")
            return result

    tasks = [
        bounded(model, prompt)
        for model in models
        for prompt in prompts
    ]
    return await asyncio.gather(*tasks)
