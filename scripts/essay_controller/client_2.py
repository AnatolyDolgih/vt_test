import requests
import time
import logging
import os

from requests.adapters import HTTPAdapter
from datetime import datetime

SERVER_URL = "https://bica-project.tw1.ru"
#SERVER_URL = "https://tutor.bicaai2023.org"

#SERVER_URL = "http://127.0.0.1:9000"

PATH_TO_LOG = "./logs/client/"
LOG_FILE = f"client_2_logs_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"

class ColorFormatter(logging.Formatter):
    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    blue = "\x1b[36;20m"
    
    FORMATS = {
        logging.DEBUG: grey,
        logging.INFO: blue,
        logging.WARNING: yellow,
        logging.ERROR: red,
        logging.CRITICAL: bold_red
    }
    
    def format(self, record):
        color = self.FORMATS.get(record.levelno)
        message = super().format(record)
        if color:
            message = color + message + self.reset
        return message

os.makedirs(PATH_TO_LOG, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Console output
console_handler = logging.StreamHandler()
console_handler.setFormatter(ColorFormatter(
    "[%(asctime)s] %(levelname)s: %(message)s"
))

# File output 
file_handler = logging.FileHandler(
    os.path.join(PATH_TO_LOG, LOG_FILE),
    encoding = "utf-8"
)
file_handler.setFormatter(logging.Formatter(
    "[%(asctime)s] %(levelname)s: %(message)s"
))

logger.addHandler(console_handler)
logger.addHandler(file_handler)

session = requests.Session()
adapter = HTTPAdapter(
    max_retries = 3,
    pool_connections = 1,
    pool_maxsize = 1
)
session.mount("https://", adapter)

error_count = 0

if __name__ == "__main__":
    theme = ""
    try:
        logger.info("Client 2 app started")
        while True:
            try:
                response = session.get(f"{SERVER_URL}/get_theme_to_bica", timeout=5)
                response.raise_for_status()
                data = response.json()
                dataTheme = data.get("theme")
                if(dataTheme != theme):
                    theme = dataTheme
                    logger.info(f"Data received: {dataTheme}")
                    re = requests.post(
                                    url="http://127.0.0.1:5050/test/4/setTheme",
                                    data=dataTheme,  # Просто строка
                                    headers={"Content-Type": "text/plain"},
                                )
        
            except requests.exceptions.RequestException as e:
                error_count += 1
                if(error_count > 50):
                    logger.error(f"Request error: {e}")
                    error_count = 0
        
            except Exception as e:
                logger.error(f"Unknown error: {e}", exc_info=True)
            
            time.sleep(0.5)
    
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    finally:
        session.close()
        logger.info("Session close")
