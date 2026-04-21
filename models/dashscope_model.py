import os, time
from .base import ModelAdapter, ModelResponse


class DashScopeModel(ModelAdapter):
    """通义千问 via DashScope（OpenAI-compatible endpoint）."""

    def is_available(self) -> bool:
        return bool(os.getenv("DASHSCOPE_API_KEY"))

    async def generate(self, prompt: str, prompt_id: str) -> ModelResponse:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        t0 = time.time()
        try:
            resp = await client.chat.completions.create(
                model=self.model,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return ModelResponse(
                model_id=self.id, model_name=self.name, prompt_id=prompt_id,
                content=resp.choices[0].message.content.strip(),
                latency_ms=round((time.time() - t0) * 1000),
            )
        except Exception as e:
            return ModelResponse(
                model_id=self.id, model_name=self.name, prompt_id=prompt_id,
                content="", latency_ms=round((time.time() - t0) * 1000), error=str(e),
            )
