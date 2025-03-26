import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Конфигурация Mistral API
know_client = {
    'api_key': os.getenv('MISTRAL_API_KEY', ''),
    'base_url': 'https://api.mistral.ai/v1',
    'model': 'mistral-small-latest',
    'max_tokens': 32000
}

# Другие настройки проекта
UPLOADS_DIR = os.getenv('UPLOADS_DIR', 'uploads')
MAX_CHARS = int(os.getenv('MAX_CHARS', '100000'))
MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 10MB по умолчанию

# Настройки логирования
LOG_DIR = os.getenv('LOG_DIR', 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'app.log')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
MAX_LOG_SIZE = int(os.getenv('MAX_LOG_SIZE', '1048576'))  # 1MB
MAX_LOG_FILES = int(os.getenv('MAX_LOG_FILES', '5'))

# Настройки безопасности
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.pptx'}
MAX_HISTORY_LENGTH = int(os.getenv('MAX_HISTORY_LENGTH', '5')) 