from loguru import logger

logger.remove()
logger.add("chaoxing.log", rotation="10 MB", level="TRACE")
