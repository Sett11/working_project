from bs4 import BeautifulSoup
import pandas as pd
import tiktoken
from logs import log_event as log_event_hf

def log_event(message):
    log_event_hf(f"FROM READTGHTML: {message}")

def validate_html(block):
    try:
        has_name = bool(block.find('div', class_='from_name'))
        has_text = bool(block.find('div', class_='text'))
        has_date = bool(block.find('div', class_='pull_right date details'))
        if not has_name or not has_text or not has_date:
            log_event(f"Блок сообщения не содержит все необходимые элементы: name={has_name}, text={has_text}, date={has_date}")
            return False
        return True
    except Exception as e:
        log_event(f"Ошибка при валидации HTML блока: {str(e)}")
        return False

def readTGhtml(file, encoding='utf8'):
    df = pd.DataFrame()
    messages = None
    len_tokens = 0
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    try:
        content = file.getvalue().decode(encoding)
        if not content.strip():
            log_event("Файл пустой")
            return None
        log_event(f"Содержимое файла начинается с: {content[:100]}")
        soup = BeautifulSoup(content, 'html.parser')
        log_event("Поиск сообщений в HTML...")
        messages = soup.find_all('div', class_='message default clearfix')
        log_event(f"Найдено сообщений: {len(messages)}")
        if not messages:
            log_event("Не найдено сообщений в файле")
            return None
    except UnicodeDecodeError:
        log_event('Ошибка декодирования файла. Проверьте кодировку.')
        return None
    except OSError as e:
        log_event(f'Ошибка при работе с файлом: {e}')
        return None
    except Exception as e:
        log_event(f'Неожиданная ошибка при чтении файла: {e}')
        return None
    valid_messages = []
    for mes in messages:
        if not validate_html(mes):
            continue
        try:
            date = mes.find('div', class_='pull_right date details').text.strip()
            name = mes.find('div', class_='from_name').text.strip()
            text = mes.find('div', class_='text').text.strip()
            if not date or not name or not text:
                log_event("Пропущено сообщение с пустыми полями")
                continue 
            len_tokens += len(enc.encode(text)) + len(enc.encode(name)) + len(enc.encode(date))
            valid_messages.append({
                'Date': pd.to_datetime(date),
                'Name': name,
                'Text': text
            })
        except Exception as e:
            log_event(f"Ошибка при обработке сообщения: {str(e)}")
            continue
    if not valid_messages:
        log_event("Не удалось извлечь корректные сообщения из файла")
        return None
    df = pd.DataFrame(valid_messages)
    log_event(f"Успешно обработано {len(valid_messages)} сообщений")
    return df, len_tokens