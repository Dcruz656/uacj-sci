import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_PATH = Path(__file__).parent.parent.parent / "local.db"
USE_SQLITE = not DATABASE_URL
