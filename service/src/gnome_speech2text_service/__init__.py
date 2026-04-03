"""Speech2Text Service

A D-Bus service that provides speech-to-text functionality for the GNOME Shell extension.
"""

__version__ = "1.2.0"
__author__ = "Kaveh Tehrani"
__email__ = "codemonkey13x@gmail.com"

__all__ = ["Speech2TextService"]


def __getattr__(name):
    value = None
    if name == "Speech2TextService":
        from .service import Speech2TextService

        value = Speech2TextService
    else:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    return value
