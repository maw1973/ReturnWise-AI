
import sys
from pathlib import Path

# 將 python-ai 加入 Python 模組搜尋路徑
BASE_DIR = Path(__file__).resolve().parent
API_DIR = BASE_DIR / "python-ai"

sys.path.insert(0, str(API_DIR))

# 載入 ReturnWise AI 的 FastAPI 應用程式
from ai_api_v2 import app
