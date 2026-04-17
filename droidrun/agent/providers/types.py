from __future__ import annotations

from dataclasses import dataclass, field


# 教程注释：ProviderVariantSpec 描述“同一家 provider 在不同鉴权模式下的具体运行时配置”。
@dataclass(frozen=True)
class ProviderVariantSpec:
    """Internal provider runtime variant for a user-facing provider family."""

    id: str
    runtime_provider_name: str
    auth_mode: str
    default_model: str | None
    models: tuple[str, ...]
    requires_api_key: bool = False
    requires_base_url: bool = False
    credential_path: str | None = None
    runtime_transport_provider_name: str | None = None
    base_url: str | None = None


# 教程注释：ProviderFamilySpec 是向用户展示的 provider 家族，内部可含多个 variant。
@dataclass(frozen=True)
class ProviderFamilySpec:
    """User-facing provider family shown during setup."""

    id: str
    display_name: str
    variants: tuple[ProviderVariantSpec, ...]
    notes: tuple[str, ...] = field(default_factory=tuple)
