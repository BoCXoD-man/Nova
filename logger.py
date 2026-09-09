from pathlib import Path
import sys

from loguru import logger


# ============================================================
# ОСНОВНАЯ ПАПКА ПРИЛОЖЕНИЯ
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
LOGS_DIR = BASE_DIR / "logs"

LOGS_DIR.mkdir(exist_ok=True)


# ============================================================
# НАСТРОЙКА LOGURU
# ============================================================

logger.remove()

logger.configure(
    extra={
        "module": "SYSTEM"
    }
)


# ============================================================
# КОНСОЛЬ
# ============================================================

logger.add(
    sys.stderr,
    level="ERROR",
    format=(
        "<red>{time:HH:mm:ss}</red> | "
        "<level>{level:<8}</level> | "
        "<cyan>{extra[module]:<10}</cyan> | "
        "{message}"
    ),
    colorize=True,
)


# ============================================================
# ФАЙЛ ЛОГА
# ============================================================

logger.add(
    LOGS_DIR / "assistant.log",
    level="DEBUG",
    rotation="10 MB",
    retention="14 days",
    encoding="utf-8",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss} | "
        "{level:<8} | "
        "{extra[module]:<10} | "
        "{message}"
    ),
)


# ============================================================
# ЛОГГЕР ДЛЯ МОДУЛЯ
# ============================================================

def get_logger(module: str):
    return logger.bind(module=module)