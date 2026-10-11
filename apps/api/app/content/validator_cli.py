"""`make validate-content` entrypoint.

TODO(T-010): real validation (Pydantic models, action-ID references, branch reachability).
Until then this only checks that CONTENT_DIR exists and says so loudly: it validates nothing.
"""

import sys

from app.core.config import get_settings


def main() -> int:
    content_dir = get_settings().content_dir
    if not content_dir.is_dir():
        print(f"ERROR: CONTENT_DIR not found: {content_dir}", file=sys.stderr)
        return 1
    print(
        f"WARNING: validate-content is a stub (T-010); no content in {content_dir} was validated."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
