from abc import ABC, abstractmethod
from typing import List


class CredentialNotFoundError(KeyError):
    """Raised when a credential key is not found."""

    pass


# 教程注释：CredentialManager 定义了统一凭证解析接口，上层只依赖“按 key 取值”和“列出可用 key”，不关心底层存储来自文件还是别的后端。
class CredentialManager(ABC):
    """Abstract base class for credential resolution."""

    @abstractmethod
    async def resolve_key(self, key: str) -> str:
        """
        Resolve and return the value for the given credential key.

        Args:
            key: Credential identifier

        Returns:
            The credential value as a string

        Raises:
            CredentialNotFoundError: If key doesn't exist
        """
        pass

    @abstractmethod
    # 教程注释：get_keys 主要用于发现当前可引用的凭证名，便于调试、校验或给上层做补全提示。
    async def get_keys(self) -> List[str]:
        """
        Get all available credential keys.

        Returns:
            List of credential identifiers
        """
        pass
