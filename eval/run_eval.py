"""`make eval`: Golden Test Suite (PRD 12.2). The runner lives in apps/api/app/golden.py."""

import sys

from app.golden import main

if __name__ == "__main__":
    sys.exit(main())
