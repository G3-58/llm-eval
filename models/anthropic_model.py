import os, time
from .base import ModelAdapter, ModelResponse


class AnthropicModel(ModelAdapter):
    def is_available(self) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY"))

    async def generate(self, prompt: str, prompt_id: str) -> ModelResponse:
        import anthropic
        client = anthropic.AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        t0 = time.time()
        try:
            resp = await client.messages.create(
                model=self.model,
                max_tokens=2048,
                temperature=self.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return ModelResponse(
                model_id=self.id, model_name=self.name, prompt_id=prompt_id,
                content=resp.content[0].text.strip(),
                latency_ms=round((time.time() - t0) * 1000),
            )
        except Exception as e:
            return ModelResponse(
                model_id=self.id, model_name=self.name, prompt_id=prompt_id,
                content="", latency_ms=round((time.time() - t0) * 1000), error=str(e),
            )
