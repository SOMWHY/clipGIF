import importlib
import pkgutil

from app.platforms.base import PlatformAdapter, PlatformInfo
from app.platforms import __path__ as platforms_path


platform_registry: list[PlatformAdapter] = []


def _discover_adapters() -> None:
    for module_info in pkgutil.iter_modules(platforms_path):
        if module_info.name in {"base", "registry"}:
            continue
        module = importlib.import_module(f"app.platforms.{module_info.name}")
        adapter = getattr(module, "ADAPTER", None)
        if isinstance(adapter, PlatformAdapter):
            register_adapter(adapter)


def register_adapter(adapter: PlatformAdapter) -> None:
    if not any(existing.name == adapter.name for existing in platform_registry):
        platform_registry.append(adapter)


def unregister_adapter(name: str) -> None:
    platform_registry[:] = [adapter for adapter in platform_registry if adapter.name != name]


def detect_platform(raw_input: str) -> PlatformAdapter | None:
    value = raw_input.strip()
    for adapter in platform_registry:
        if adapter.match(value):
            return adapter
    return None


def list_platforms() -> list[PlatformInfo]:
    return [adapter.info() for adapter in platform_registry]


_discover_adapters()
