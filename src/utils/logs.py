import logging
from logging.handlers import RotatingFileHandler

red = "\033[31m"
blue = "\033[34m"
green = "\033[32m"
yellow = "\033[33m"
orange = "\033[38;5;208m"
reset = "\033[0m"


class ColorFormatter(logging.Formatter):
    def format(self, record) -> str:
        if record.levelno == logging.DEBUG:
            color = blue
        elif record.levelno == logging.INFO:
            color = green
        elif record.levelno == logging.WARNING:
            color = yellow
        elif record.levelno == logging.CRITICAL:
            color = orange
        elif record.levelno == logging.ERROR:
            color = red
        else:
            color = reset

        record.levelname = f"{color}{record.levelname}{reset}"

        message = super().format(record)
        return message


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_handler = logging.StreamHandler()
formatter = ColorFormatter("%(asctime)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)


file_handler = RotatingFileHandler("app.log", maxBytes=1024 * 1024, backupCount=3)
# rotate file after it reaches 1MB, keep 3 backups

file_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(name)s -%(message)s"
)
file_handler.setFormatter(file_formatter)
file_handler.setLevel(logging.WARNING)


logger.addHandler(file_handler)
logger.addHandler(console_handler)

if __name__ == "__main__":
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.critical("Critical message")
    logger.error("Error message")
