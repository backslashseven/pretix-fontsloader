__version__ = "1.0.0"

try:
    from .apps import PluginApp as PretixPluginMeta
except RuntimeError:
    pass
