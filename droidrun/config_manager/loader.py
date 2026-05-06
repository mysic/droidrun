"""Config loading with platform-aware user config and migrations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

import platformdirs  # type: ignore[import-not-found]
import yaml

from .config_manager import DroidConfig
from .migrations import CURRENT_VERSION, migrate


class OutdatedConfigError(Exception):
    """Raised when user config is missing _version field."""

    pass



# 教程注释：ConfigLoader 统一处理配置文件的查找、首次初始化和版本迁移，是配置系统的入口门面。
class ConfigLoader:
    """Unified config loading with user config support."""

    APP_NAME = "droidrun"
    CONFIG_FILE = "config.yaml"

    @classmethod
    def get_user_config_dir(cls) -> Path:
        return Path(platformdirs.user_config_dir(cls.APP_NAME))

    @classmethod
    def get_user_config_path(cls) -> Path:
        return cls.get_user_config_dir() / cls.CONFIG_FILE

    @classmethod
    def get_project_config_path(cls) -> Path:
        """Get project config path (droidrun/config.yaml in project root)."""
        # Find the project root by looking for the droidrun package directory
        current_file = Path(__file__).resolve()
        # Go up from config_manager/loader.py to droidrun/ then to project root
        project_root = current_file.parent.parent.parent
        return project_root / "droidrun" / cls.CONFIG_FILE

    # 教程注释：load 按"显式参数 -> 环境变量 -> 项目目录 -> 用户目录 -> 默认初始化"的顺序决定最终使用哪份配置。
    @classmethod
    def load(cls, config_path: Optional[str] = None) -> DroidConfig:
        """
        Load config with resolution order:
        1. Explicit config_path argument
        2. DROIDRUN_CONFIG env var
        3. Project config (droidrun/config.yaml in project root)
        4. User config (~/.config/droidrun/config.yaml)
        5. Package defaults (creates user config)
        """
        if config_path:
            return cls._load_user_config(Path(config_path))
    
        env_config = os.environ.get("DROIDRUN_CONFIG")
        if env_config and Path(env_config).exists():
            return cls._load_user_config(Path(env_config))
    
        # Try project config first
        project_config_path = cls.get_project_config_path()
        if project_config_path.exists():
            return cls._load_user_config(project_config_path)
    
        user_config_path = cls.get_user_config_path()
    
        if user_config_path.exists():
            return cls._load_user_config(user_config_path)
    
        return cls._init_user_config()

    @classmethod
    def get_active_config_path(cls, config_path: Optional[str] = None) -> Path:
        """Resolve which config path is active under current precedence rules."""
        if config_path:
            return Path(config_path)

        env_config = os.environ.get("DROIDRUN_CONFIG")
        if env_config and Path(env_config).exists():
            return Path(env_config)

        project_config_path = cls.get_project_config_path()
        if project_config_path.exists():
            return project_config_path

        user_config_path = cls.get_user_config_path()
        if user_config_path.exists():
            return user_config_path

        return user_config_path

    @classmethod
    def _load_user_config(cls, user_config_path: Path) -> DroidConfig:
        """Load user config and run migrations."""
        # 教程注释：加载后会先执行迁移，再在版本升级时自动回写新结构，减少手工维护成本。
        with open(user_config_path, "r", encoding="utf-8") as f:
            user_dict = yaml.safe_load(f) or {}

        if "_version" not in user_dict:
            raise OutdatedConfigError(
                f"Config at {user_config_path} is outdated (missing _version).\n"
                "Please update your config based on the latest example:\n"
                "https://github.com/droidrun/droidrun/blob/main/droidrun/config_example.yaml"
            )

        old_version = user_dict["_version"]
        user_dict = migrate(user_dict)

        if user_dict.get("_version", 0) > old_version:
            cls._save_dict(user_dict, user_config_path)

        return DroidConfig.from_dict(user_dict)

    @classmethod
    def _init_user_config(cls) -> DroidConfig:
        """Create user config from defaults on first run."""
        config = DroidConfig()
        cls.save(config)
        return config

    @classmethod
    def save(cls, config: DroidConfig) -> Path:
        """Save config to user config path."""
        config_dict = config.to_dict()
        config_dict["_version"] = CURRENT_VERSION
        return cls._save_dict(config_dict, cls.get_user_config_path())

    @classmethod
    def save_to_path(cls, config: DroidConfig, path: Path) -> Path:
        """Save config to an explicit path."""
        config_dict = config.to_dict()
        config_dict["_version"] = CURRENT_VERSION
        return cls._save_dict(config_dict, path)

    @classmethod
    def _save_dict(cls, config_dict: Dict[str, Any], path: Path) -> Path:
        """Save config dict to path, preserving comments when possible."""
        path.parent.mkdir(parents=True, exist_ok=True)

        # Try round-trip YAML updates first so existing comments are preserved.
        try:
            from ruamel.yaml import YAML  # type: ignore[import-not-found]

            yaml_rt = YAML()
            yaml_rt.preserve_quotes = True
            yaml_rt.indent(mapping=2, sequence=4, offset=2)

            existing: Dict[str, Any] = {}
            if path.exists():
                with open(path, "r", encoding="utf-8") as f:
                    loaded = yaml_rt.load(f)
                    if isinstance(loaded, dict):
                        existing = loaded

            merged = cls._merge_nested(existing, config_dict)
            with open(path, "w", encoding="utf-8") as f:
                yaml_rt.dump(merged, f)
            return path
        except Exception:
            # Fallback to plain YAML dump if ruamel is unavailable.
            pass

        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(config_dict, f, default_flow_style=False, sort_keys=False)
        return path

    @staticmethod
    def _merge_nested(existing: Any, incoming: Any) -> Any:
        """Recursively merge incoming values into existing structure."""
        if isinstance(existing, dict) and isinstance(incoming, dict):
            for key, value in incoming.items():
                if key in existing:
                    existing[key] = ConfigLoader._merge_nested(existing[key], value)
                else:
                    existing[key] = value
            return existing
        return incoming
