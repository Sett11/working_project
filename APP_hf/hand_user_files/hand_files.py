import unicodedata
import tiktoken
import re
from collections import deque
import pandas as pd
import io
from hand_user_files.readWAtxt import readWAtxt
from hand_user_files.readTGjson import readTGjson
from hand_user_files.readTGhtml import readTGhtml
from hand_logs.mylogger import Logger, LOG_FILE
import logging

logger = Logger('app_logger', LOG_FILE, level=logging.INFO)

def log_event(message):
    logger.info(f"FROM HAND_FILES: {message}")

def hand_names(names):
    name_code = {}
    code_name = {}
    indexes = iter(range(100))
    for on in names:
        tname = 'У' + str(next(indexes))
        name_code[on] = tname
        code_name[tname] = on
    return name_code, code_name

def remove_special_chars(text):
    arr_text = text.split(' ')
    for i in range(len(arr_text)):
        arr_text[i] = ''.join(c for c in arr_text[i] if unicodedata.category(c).startswith(('L', 'N')))
    return ' '.join(arr_text)

def clearText(content):
    content = remove_special_chars(content) # удаляем спец символы
    content = re.sub('<.*?>', ' ', content).strip() # html code
    content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content) # ссылки
    content = re.sub('&lt;br&gt;|&lt;br /&gt;|&nbsp;|\n', ' ', content) # спец символы
    content = re.sub(r'[^A-zА-Яа-яЁё0-9 .,:;?!]', ' ', content) # !!! пока пробуем оставлять только русские и английские буквы, цифры и знаки препинания
    content = re.sub('[ ]{2,10}', ' ', content).strip() # лишние пробелы
    return content

def detect_file_type(file_content):
    try:
        # Пробуем декодировать как JSON
        content_str = file_content.decode("utf-8").strip().lower()
        if content_str[0] in "{[":
            return "json"
        # Проверяем на HTML
        if "<html" in content_str or "<!DOCTYPE html" in content_str:
            return "html"
        # Если не JSON и не HTML, считаем текстовым файлом
        return "txt"
    except UnicodeDecodeError:
        return

def content_pre_process(file_obj, anonymize_names=True, save_datetime=False, max_len_context="100", time_choise=None):
    anonymize_names = str(anonymize_names).lower() == 'true'
    save_datetime = str(save_datetime).lower() == 'true'
    max_len_context = int(max_len_context)
    time_choise = int(time_choise)
    log_event(f"Параметры обрабтки: {anonymize_names}, {save_datetime}, {max_len_context}, {time_choise}")
    try:
        df = None
        if hasattr(file_obj, 'read'):
            file_content = file_obj.read()
        else:
            file_content = file_obj
        file_ext = detect_file_type(file_content)
        file_obj = io.BytesIO(file_content)
        if file_ext is None:
            log_event("Не удалось определить тип файла")
            return None, None
        if file_ext == "json":
            log_event("Определен тип файла: JSON")
            df = readTGjson(file_obj)
        elif file_ext == "html":
            log_event("Определен тип файла: HTML")
            df = readTGhtml(file_obj)
        elif file_ext == "txt":
            log_event("Определен тип файла: TXT")
            df = readWAtxt(file_obj)
        else:
            log_event('Ожидается объект BytesIO')
            return None, None
        if df is None or df.empty:
            log_event('Не удалось прочитать файл')
            return None, None
        if 'Name' not in df.columns:
            log_event('Файл не содержит необходимые колонки')
            return None, None
        log_event(f"Успешно прочитан файл. Количество строк: {len(df)}")
        df['Name'] = df['Name'].apply(lambda x: remove_special_chars(x))
        df['Text'] = df['Text'].apply(lambda x: clearText(x))
        name_code, code_name = hand_names(df.Name.unique()) if anonymize_names else (None, None)
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
        content = deque()
        len_tokens = 0
        start_date = df['Date'].iloc[-1] - pd.Timedelta(hours=time_choise)
        for index in df.index[::-1]:
            new_content = (name_code[df.loc[index, 'Name']] if anonymize_names else df.loc[index, 'Name']) +\
            (('&' + str(df.loc[index, 'Date'])) if save_datetime else '') +\
            (': ' if not save_datetime else '> ') + re.sub('\n', ' ', df.loc[index, 'Text']) + '\n'
            if not re.sub(r'[ \n]', '' ,new_content.split(': ')[-1]):
                continue
            new_len = len(enc.encode(new_content))
            if (new_len + len_tokens > max_len_context) or (df.loc[index, 'Date'] < start_date):
                break
            content.appendleft(new_content)
            len_tokens += new_len
        log_event(f"Всего сообщений {df.shape[0]}, попало в контент {df.shape[0] - index}")
        return ''.join(content), code_name
    except FileNotFoundError:
        log_event(f"Файл не найден.")
    except UnicodeDecodeError:
        log_event(f"Ошибка декодирования файла. Проверьте кодировку.")
    except ValueError as e:
        log_event(f"Ошибка преобразования данных: {e}")
    except KeyError as e:
        log_event(f"Ключ не найден в DataFrame: {e}")
    except TypeError as e:
        log_event(f"Ошибка типа данных: {e}")
    except Exception as e:
        log_event(f"FROM HAND_FILES: Произошла ошибка: {e}")
    return None, None