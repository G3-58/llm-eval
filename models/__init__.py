from .openai_model import OpenAIModel
from .anthropic_model import AnthropicModel
from .dashscope_model import DashScopeModel
from .moonshot_model import MoonshotModel

PROVIDER_MAP = {
    "openai":    OpenAIModel,
    "anthropic": AnthropicModel,
    "dashscope": DashScopeModel,
    "moonshot":  MoonshotModel,
}

def build_models(model_configs: list[dict]) -> list:
    models = []
    for cfg in model_configs:
        cls = PROVIDER_MAP.get(cfg["provider"])
        if cls is None:
            print(f"  [!] Unknown provider: {cfg['provider']}, skipping.")
            continue
        m = cls(cfg)
        if m.is_available():
            models.append(m)
        else:
            print(f"  [skip] {cfg['name']} — API key not set")
    return models
