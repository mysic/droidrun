"""Config migration system."""

from typing import Dict, Any, List
import importlib
import pkgutil
from pathlib import Path


CURRENT_VERSION = 5


# 教程注释：这里会自动发现所有版本迁移模块，避免手工维护迁移列表。
def get_migrations() -> List:
    """Discover and load all migration modules."""
    migrations = []
    migrations_dir = Path(__file__).parent

    for _, name, _ in pkgutil.iter_modules([str(migrations_dir)]):
        if name.startswith("v") and name[1:4].isdigit():
            module = importlib.import_module(f".{name}", package=__name__)
            if hasattr(module, "VERSION") and hasattr(module, "migrate"):
                migrations.append(module)

    return sorted(migrations, key=lambda m: m.VERSION)


# 教程注释：migrate 会按版本顺序执行所有待运行迁移，把旧配置升级到当前版本。
def migrate(config: Dict[str, Any]) -> Dict[str, Any]:
    """Run all pending migrations on config."""
    version = config.get("_version", 0)

    if version >= CURRENT_VERSION:
        return config

    migrations = get_migrations()

    for migration in migrations:
        if migration.VERSION > version:
            config = migration.migrate(config)
            config["_version"] = migration.VERSION

    return config
