from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

WEB_DIRECTORY = "./js"

__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS', 'WEB_DIRECTORY']

try:
    from .nodes import comfy_entrypoint  # noqa: F401
    __all__.append('comfy_entrypoint')
except ImportError:
    pass