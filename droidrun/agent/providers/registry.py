from __future__ import annotations

from droidrun.agent.providers.types import (
    ProviderFamilySpec,
    ProviderVariantSpec,
)
from droidrun.config_manager.credential_paths import (
    ANTHROPIC_OAUTH_CREDENTIAL_PATH,
    GEMINI_OAUTH_CREDENTIAL_PATH,
    OPENAI_OAUTH_CREDENTIAL_PATH,
)


# 教程注释：VARIANT_ENV_KEY_SLOT 定义“provider variant -> env_keys 槽位名”的统一映射。
# Canonical mapping from variant ID to env-key slot name.
# Imported by setup_service, configure_wizard, config_manager, and TUI.
VARIANT_ENV_KEY_SLOT: dict[str, str] = {
    "GoogleGenAI": "google",
    "OpenAIResponses": "openai",
    "Anthropic": "anthropic",
    "ZAI": "zai",
    "ZAI_Coding": "zai",
    "MiniMax": "minimax",
}


# 教程注释：PROVIDER_FAMILIES 是 setup wizard 的主数据源，维护展示名、鉴权模式和模型列表。
PROVIDER_FAMILIES: tuple[ProviderFamilySpec, ...] = (
    ProviderFamilySpec(
        id="gemini",
        display_name="Gemini",
        variants=(
            ProviderVariantSpec(
                id="GoogleGenAI",
                runtime_provider_name="GoogleGenAI",
                auth_mode="api_key",
                default_model="gemini-3.1-pro-preview",
                models=(
                    "gemini-3-flash-preview",
                    "gemini-3.1-pro-preview",
                    "gemini-3.1-flash-lite-preview",
                ),
                requires_api_key=True,
            ),
            ProviderVariantSpec(
                id="gemini_oauth_code_assist",
                runtime_provider_name="gemini_oauth_code_assist",
                auth_mode="oauth",
                default_model="gemini-3.1-pro-preview",
                models=(
                    "gemini-3-flash-preview",
                    "gemini-3.1-pro-preview",
                    "gemini-3.1-flash-lite-preview",
                ),
                credential_path=str(GEMINI_OAUTH_CREDENTIAL_PATH),
            ),
        ),
    ),
    ProviderFamilySpec(
        id="openai",
        display_name="OpenAI",
        variants=(
            ProviderVariantSpec(
                id="OpenAIResponses",
                runtime_provider_name="OpenAIResponses",
                auth_mode="api_key",
                default_model="gpt-5.4",
                models=(
                    "gpt-5.4",
                    "gpt-5.4-mini",
                    "gpt-5.4-nano",
                ),
                requires_api_key=True,
            ),
            ProviderVariantSpec(
                id="openai_oauth",
                runtime_provider_name="openai_oauth",
                auth_mode="oauth",
                default_model="gpt-5.4",
                models=(
                    "gpt-5.4",
                    "gpt-5.4-mini",
                    "gpt-5.3-codex",
                ),
                credential_path=str(OPENAI_OAUTH_CREDENTIAL_PATH),
            ),
        ),
        notes=("OpenAI OAuth uses a restricted model catalog.",),
    ),
    ProviderFamilySpec(
        id="anthropic",
        display_name="Anthropic",
        variants=(
            ProviderVariantSpec(
                id="Anthropic",
                runtime_provider_name="Anthropic",
                auth_mode="api_key",
                default_model="claude-sonnet-4-6",
                models=(
                    "claude-sonnet-4-6",
                    "claude-opus-4-6",
                    "claude-haiku-4-5",
                ),
                requires_api_key=True,
            ),
            ProviderVariantSpec(
                id="anthropic_oauth",
                runtime_provider_name="anthropic_oauth",
                auth_mode="oauth",
                default_model="claude-sonnet-4-6",
                models=(
                    "claude-sonnet-4-6",
                    "claude-opus-4-6",
                    "claude-haiku-4-5",
                ),
                credential_path=str(ANTHROPIC_OAUTH_CREDENTIAL_PATH),
            ),
        ),
    ),
    ProviderFamilySpec(
        id="ollama",
        display_name="Ollama",
        variants=(
            ProviderVariantSpec(
                id="Ollama",
                runtime_provider_name="Ollama",
                auth_mode="none",
                default_model="llama3.2:3b",
                models=(),
                requires_base_url=True,
                base_url="http://localhost:11434",
            ),
        ),
    ),
    ProviderFamilySpec(
        id="openai_like",
        display_name="OpenAI Compatible",
        variants=(
            ProviderVariantSpec(
                id="OpenAILike",
                runtime_provider_name="OpenAILike",
                auth_mode="api_key",
                default_model=None,
                models=(),
                requires_api_key=True,
                requires_base_url=True,
            ),
        ),
        notes=(
            "Use for OpenRouter, LM Studio, vLLM, and other OpenAI-compatible endpoints.",
        ),
    ),
    ProviderFamilySpec(
        id="minimax",
        display_name="MiniMax",
        variants=(
            ProviderVariantSpec(
                id="MiniMax",
                runtime_provider_name="MiniMax",
                runtime_transport_provider_name="OpenAILike",
                auth_mode="api_key",
                default_model="MiniMax-M2.7",
                models=(
                    "MiniMax-M2.7",
                    "MiniMax-M2.5-highspeed",
                ),
                requires_api_key=True,
                requires_base_url=True,
                base_url="https://api.minimaxi.chat/v1",
            ),
        ),
    ),
    ProviderFamilySpec(
        id="zai",
        display_name="ZAI",
        variants=(
            ProviderVariantSpec(
                id="ZAI",
                runtime_provider_name="ZAI",
                runtime_transport_provider_name="OpenAILike",
                auth_mode="api_key",
                default_model="glm-5",
                models=(
                    "glm-5",
                    "glm-5v-turbo",
                    "glm-4.7",
                ),
                requires_api_key=True,
                requires_base_url=True,
                base_url="https://api.z.ai/api/paas/v4",
            ),
            ProviderVariantSpec(
                id="ZAI_Coding",
                runtime_provider_name="ZAI",
                runtime_transport_provider_name="OpenAILike",
                auth_mode="coding_api",
                default_model="glm-4.7",
                models=(
                    "glm-4.7",
                ),
                requires_api_key=True,
                requires_base_url=True,
                base_url="https://api.z.ai/api/coding/paas/v4",
            ),
        ),
        notes=(
            "ZAI is exposed as a first-class provider family while reusing the OpenAI-compatible transport.",
            "Use auth mode `coding_api` for the GLM Coding Plan endpoint.",
        ),
    ),
)


# 教程注释：列出所有可选 provider family，供 UI/Wizard 构建选项。
def list_provider_families() -> tuple[ProviderFamilySpec, ...]:
    return PROVIDER_FAMILIES


# 教程注释：按 family_id 查找 provider 家族；找不到会抛 KeyError。
def get_provider_family(family_id: str) -> ProviderFamilySpec:
    for family in PROVIDER_FAMILIES:
        if family.id == family_id:
            return family
    raise KeyError(f"Unknown provider family: {family_id}")


# 教程注释：列出某个 family 支持的 auth mode，用于二级选择。
def list_auth_modes(family_id: str) -> tuple[str, ...]:
    family = get_provider_family(family_id)
    return tuple(variant.auth_mode for variant in family.variants)


# 教程注释：把 family + auth_mode 解析为最终 ProviderVariantSpec。
def resolve_provider_variant(
    family_id: str, auth_mode: str | None = None
) -> ProviderVariantSpec:
    family = get_provider_family(family_id)
    if auth_mode is None:
        if len(family.variants) != 1:
            raise ValueError(
                f"Provider family {family_id} requires an auth mode selection."
            )
        return family.variants[0]
    for variant in family.variants:
        if variant.auth_mode == auth_mode:
            return variant
    raise KeyError(f"Unknown auth mode {auth_mode!r} for provider family {family_id}")


# 教程注释：读取某个 variant 可选模型列表，供配置向导展示。
def list_models_for_variant(
    family_id: str, auth_mode: str | None = None
) -> tuple[str, ...]:
    return resolve_provider_variant(family_id, auth_mode).models


# 教程注释：把模型别名规范化为 canonical model id，避免配置里写入前缀别名。
def normalize_model_id_for_variant(
    family_id: str, auth_mode: str | None, model_id: str
) -> str:
    """Normalize accepted model aliases to the canonical model id for a variant."""
    variant = resolve_provider_variant(family_id, auth_mode)
    allowed_model_ids = set(variant.models)
    if model_id in allowed_model_ids:
        return model_id

    alias_prefixes: tuple[str, ...] = ()
    if family_id == "openai" and auth_mode == "api_key":
        alias_prefixes = ("openai/",)
    elif family_id == "openai" and auth_mode == "oauth":
        alias_prefixes = ("openai-codex/", "openai/")

    for prefix in alias_prefixes:
        if model_id.startswith(prefix):
            normalized = model_id[len(prefix):]
            if normalized in allowed_model_ids:
                return normalized

    return model_id
