"""Entry point for Vercel serverless — Mangum adapts FastAPI (ASGI) to Lambda handler."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.api.main import app  # noqa: F401
from mangum import Mangum

handler = Mangum(app, lifespan="off")

