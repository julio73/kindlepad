import logging

import uvicorn

from server.app import DEFAULT_CONFIG_PATH, create_app
from server.config import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

app = create_app()

if __name__ == "__main__":
    config = load_config(DEFAULT_CONFIG_PATH)
    uvicorn.run(app, host=config.server.host, port=config.server.port)
