import os
from loguru import logger

logger.remove()
_log_dir = os.environ.get("FUCKCOURSE_LOG_DIR", "")
_log_path = os.path.join(_log_dir, "chaoxing.log") if _log_dir else "chaoxing.log"
logger.add(_log_path, rotation="10 MB", level="TRACE")
