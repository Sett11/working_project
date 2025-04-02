import pandas as pd
import re
from logs import log_event as log_event_hf

def log_event(message):
    log_event_hf(f"FROM READWATXT: {message}")

def validate_txt(line):
    """
    Checking structure txt file
    """
    # Более гибкое регулярное выражение для проверки структуры
    return re.match(r'^\d{2}\.\d{2}\.\d{4}, \d{2}:\d{2} - [^:]+: .+$', line.strip()) is not None


def readWAtxt(file, encoding='utf8'):
    """
    Read whatsApp's txt and take only messages
    Return DataFrame
    """
    df = pd.DataFrame()
    text = ''
    try:
        text = file.getvalue().decode(encoding)
    except UnicodeDecodeError:
        log_event(f"Ошибка декодирования файла {file}. Проверьте кодировку.")
        return None
    except OSError as e:
        log_event(f"Ошибка при работе с файлом {file}: {e}")
        return None
    if not text:
        log_event("Файл пуст")
        return None
    # Разбиваем текст на сообщения, сохраняя первую строку
    text = re.split(r'\n(?=\d\d.\d\d.\d\d\d\d)', text)
    for one in text:
        # Пропускаем пустые строки и системные сообщения
        if not one.strip() or re.search('‎', one):
            continue
        mes = re.sub(r'\n', ' ', one).strip()
        if not validate_txt(mes):
            log_event(f'Некорректная структура строки: {mes}...')
            continue 
        try:
            tone = re.split(' - |: ', mes)
            if len(tone) < 3:
                log_event(f'Некорректный формат сообщения: {mes[:50]}...')
                continue
                
            df = pd.concat([df,
                            pd.DataFrame([{'Date': pd.to_datetime(tone[0], format='%d.%m.%Y, %H:%M'), 
                                         'Name': tone[1],
                                         'Text': ' '.join(tone[2:]).strip()}])
                            ],
                           ignore_index=True)
        except Exception as e:
            log_event(f'Ошибка при обработке строки: {str(e)}')
            continue
    if df.empty:
        log_event("Не удалось извлечь сообщения из файла")
        return None
    return df