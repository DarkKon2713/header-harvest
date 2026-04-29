import logging

import uvicorn

from app.config import HEADLESS, MAX_CONCURRENT, MAX_TIMEOUT, PORT, PROXY_URL
from app.main import app  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    logger.info(
        "HeaderHarvest starting | port=%d headless=%s timeout=%dms max_concurrent=%d",
        PORT, HEADLESS, MAX_TIMEOUT, MAX_CONCURRENT,
    )
    if PROXY_URL:
        logger.info("Global proxy: %s", PROXY_URL)
    uvicorn.run(app, host="0.0.0.0", port=PORT)
