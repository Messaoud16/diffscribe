from __future__ import annotations

from typing import Optional

LANGUAGE_EXTENSIONS = {
    "python": {".py"},
    "javascript": {".js", ".jsx", ".mjs", ".cjs"},
}


def detect_language(filename: str) -> Optional[str]:
    for language, extensions in LANGUAGE_EXTENSIONS.items():
        for extension in extensions:
            if filename.endswith(extension):
                return language
    return None
