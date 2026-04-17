import logging
from typing import Any, Dict, Optional

import yaml

from droidrun.config_manager.path_resolver import PathResolver
from droidrun.credential_manager.credential_manager import (
    CredentialManager,
    CredentialNotFoundError,
)

logger = logging.getLogger("droidrun")


# 教程注释：FileCredentialManager 是默认实现，负责把内存 dict、CredentialsConfig 或 YAML 文件统一转换成可查询的 secrets 映射。
class FileCredentialManager(CredentialManager):
    """
    Credential manager that supports both dict and YAML file sources.
    """

    def __init__(self, credentials: Any):
        """
        Initialize credential manager from dict or file path.

        Args:
            credentials: Either dict or string (file path) or CredentialsConfig
        """
        self.path: Optional[str] = None
        self.secrets = self._load(credentials)

        if self.path:
            logger.debug(f"✅ Loaded {len(self.secrets)} secrets from {self.path}")
        else:
            logger.debug(f"✅ Loaded {len(self.secrets)} secrets from in-memory dict")

    # 教程注释：_load 是总分发入口，用输入类型决定走哪条加载路径，从而屏蔽不同来源的差异。
    def _load(self, credentials: Any) -> Dict[str, str]:
        """Load credentials from dict or file."""
        from droidrun.config_manager.config_manager import CredentialsConfig

        # Dict mode
        if isinstance(credentials, dict):
            return self._load_from_dict(credentials)

        # CredentialsConfig mode
        if isinstance(credentials, CredentialsConfig):
            if not credentials.enabled:
                logger.debug("Credentials disabled in config")
                return {}
            self.path = credentials.file_path
            return self._load_from_file(credentials.file_path)

        # String mode (direct file path)
        if isinstance(credentials, str):
            self.path = credentials
            return self._load_from_file(credentials)

        logger.warning(f"Unknown credentials type: {type(credentials)}")
        return {}

    # 教程注释：dict 模式适合测试或嵌入式场景，逻辑只保留“非空字符串”类型的键值。
    def _load_from_dict(self, credentials_dict: dict) -> Dict[str, str]:
        """Load credentials from in-memory dict."""
        secrets = {}
        for secret_id, secret_value in credentials_dict.items():
            if isinstance(secret_value, str) and secret_value:
                secrets[secret_id] = secret_value
            else:
                logger.warning(
                    f"Skipped invalid secret: {secret_id} (type={type(secret_value)})"
                )
        return secrets

    # 教程注释：文件模式支持更丰富的 YAML 结构，既可以写简单键值，也可以为每个 secret 单独声明 enabled 开关。
    def _load_from_file(self, file_path: str) -> Dict[str, str]:
        """
        Load credentials from YAML file.

        File format:
            secrets:
              MY_PASSWORD:
                value: "secret123"
                enabled: true
              SIMPLE_KEY: "simple_value"  # Auto-enabled

        Returns:
            Dict of enabled secrets {secret_id: secret_value}
        """
        path = PathResolver.resolve(file_path, must_exist=True)
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        if not data or "secrets" not in data:
            logger.warning(f"No 'secrets' section found in {path}")
            return {}

        secrets = {}
        for secret_id, secret_data in data["secrets"].items():
            if isinstance(secret_data, dict):
                enabled = secret_data.get("enabled", True)
                value = secret_data.get("value", "")
            else:
                enabled = True
                value = secret_data

            if enabled and value:
                secrets[secret_id] = value
                logger.debug(f"Loaded secret: {secret_id}")
            else:
                logger.debug(
                    f"Skipped secret: {secret_id} (enabled={enabled}, has_value={bool(value)})"
                )

        return secrets

    # 教程注释：resolve_key 是实际取密钥值的入口，不存在时会抛出带可用键列表的错误，方便定位配置引用问题。
    async def resolve_key(self, key: str) -> str:
        """Get secret value by key."""
        logger.debug(f"🔑 Accessing secret: '{key}'")

        if key not in self.secrets:
            available = list(self.secrets.keys())
            raise CredentialNotFoundError(
                f"Secret '{key}' not found. Available: {available}"
            )

        return self.secrets[key]

    # 教程注释：get_keys 暴露当前已加载成功的密钥名集合，让上层只依赖抽象接口即可完成发现与校验。
    async def get_keys(self) -> list[str]:
        """Get all available credential keys."""
        return list(self.secrets.keys())

    def has_credential(self, secret_id: str) -> bool:
        """Check if secret ID exists."""
        return secret_id in self.secrets

    def __repr__(self) -> str:
        """String representation."""
        count = len(self.secrets)
        if self.path:
            return f"<FileCredentialManager path={self.path} secrets={count}>"
        return f"<FileCredentialManager mode=dict secrets={count}>"
