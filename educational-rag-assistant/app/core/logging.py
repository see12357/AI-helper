# Настройка логирования
import logging
import sys
from app.core.config import settings

def setup_logging():
    """Настройка логирования для приложения"""
    
    # Форматтер
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Хэндлер для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO if not settings.DEBUG else logging.DEBUG)
    root_logger.addHandler(console_handler)
    
    # Отключаем избыточное логирование некоторых библиотек
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING if not settings.DEBUG else logging.INFO)
    
    return root_logger

# Инициализируем логирование при импорте модуля
logger = setup_logging()