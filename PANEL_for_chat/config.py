# Конфигурация Mistral API
know_client = {
    'api_key': '',
    'base_url': 'https://api.mistral.ai/v1',
    'model': 'mistral-small-latest',
    'max_tokens': 32000
}

# Другие настройки проекта
UPLOADS_DIR = 'uploads'
MAX_CHARS = 110000
MAX_FILE_SIZE = 104857600  # 100MB по умолчанию

# Настройки логирования
LOG_FILE = 'app.log'
LOG_LEVEL = 'INFO'
MAX_LOG_SIZE = 1048576  # 1MB

# Настройки безопасности
ALLOWED_EXTENSIONS = {'.txt', '.pdf', '.docx', '.pptx'}
MAX_HISTORY_LENGTH = 5