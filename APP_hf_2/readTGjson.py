import json
import pandas as pd
from logs import log_event as log_event_hf
from jsonschema import validate, ValidationError

def log_event(message):
    log_event_hf(f"FROM READTGJSON: {message}")

# Определение схемы для валидации
schema = {
    "type": "object",
    "properties": {
        "messages": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "date": {"type": "string"},
                    "type": {"type": "string"},
                    "text": {
                        "type": ["string", "array"],
                        "items": {
                            "type": ["string", "object"]
                        }
                    },
                    "from_id": {"type": ["integer", "string"]},
                    "from": {"type": "string"},
                    "actor_id": {"type": ["integer", "string"]},
                    "actor": {"type": "string"}
                },
                "required": ["id", "date", "type", "text"],
                "anyOf": [
                    {
                        "required": ["from", "from_id"]
                    },
                    {
                        "required": ["actor", "actor_id"]
                    }
                ]
            }
        }
    },
    "required": ["messages"]
}

def validate_json(file):
    """
    Проверка структуры JSON файла
    """
    try:
        validate(instance=file, schema=schema)
    except ValidationError as e:
        log_event(f"Ошибка валидации JSON: {e.message}")
        return False
    return True
        
def readTGjson(file, encoding='utf8'):
    """
    Чтение JSON Telegram и извлечение только сообщений
    Возвращает DataFrame
    """
    df = pd.DataFrame()
    jdata = None
    try:
        jdata = json.loads(file.getvalue().decode(encoding))
    except json.JSONDecodeError:
        log_event(f"Ошибка декодирования JSON.")
        return None
    except UnicodeDecodeError:
        log_event(f"Ошибка декодирования файла. Проверьте кодировку.")
        return None
    except OSError as e:
        log_event(f"Ошибка при работе с файлом: {e}")
        return None
    if not jdata or not validate_json(jdata):
        log_event('Некорректная структура JSON файла')
        return None
    for one in jdata['messages']:
        if one['type'] != 'message':
            continue
        Name = one['from']
        Name_id = one['from_id']
        id_mess = one['id']
        dN = pd.to_datetime(one['date'], format='%Y-%m-%dT%H:%M:%S')
        if isinstance(one['text'], str):
            Text = one['text']
        else:
            Text = ' '.join(i if isinstance(i, str) else i['text'] for i in one['text'])
        df = pd.concat([df,
                        pd.DataFrame([{'id': id_mess, 'Date': dN, 'Name': Name, 'Name_id': Name_id, 'Text': Text}])],
                       ignore_index=True)
        
    return df