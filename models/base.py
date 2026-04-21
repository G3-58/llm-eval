"""Base adapter interface — every model implements generate()."""
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ModelResponse:
    model_id: str
    model_name: str
    prompt_id: str
    content: str           # 模型回答
    latency_ms: float      # 响应时间
    error: str | None = None   # 出错时记录


class ModelAdapter(ABC):
    def __init__(self, cfg: dict):
        self.id   = cfg["id"]
        self.name = cfg["name"]
        self.model = cfg["model"]
        self.temperature = cfg.get("temperature", 0.7)

    @abstractmethod
    async def generate(self, prompt: str, prompt_id: str) -> ModelResponse:
        ...

    def is_available(self) -> bool:
        """Return False if the required API key is missing."""
        return True
