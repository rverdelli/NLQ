import os
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = "claude-sonnet-4-20250514"
DATABASE_PATH = os.path.join(os.path.dirname(__file__), "ecommerce.db")
QUERY_TIMEOUT_SECONDS = 5
MAX_QUERY_ROWS = 1000
