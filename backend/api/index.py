"""Entry point for Vercel serverless - Mangum adapts FastAPI (ASGI) to Lambda handler."""
import sys
import os
from pathlib import Path

# Ensure project root is in sys.path so 'backend.*' imports resolve correctly
# both locally and on Vercel's serverless environment
_here = Path(__file__).resolve()
_project_root = _here.parent.parent.parent  # backend/api/index.py -> root
for _p in [str(_project_root), str(_project_root / 'backend')]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

from backend.api.main import app  # noqa: F401
from mangum import Mangum

handler = Mangum(app, lifespan="off")
