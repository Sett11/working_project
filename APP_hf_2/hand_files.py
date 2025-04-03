import unicodedata
import tiktoken
import re
from collections import deque
import pandas as pd
import datetime
import io
from readWAtxt import readWAtxt
from readTGjson import readTGjson
from readTGhtml import readTGhtml
from logs import log_event as log_event_hf

def log_event(message):
    log_event_hf(f"FROM HAND_FILES: {message}")

def hand_names(names):
    """
    The function receives a numpy.ndarray with unique names and returns 2 dictionaries: 1. name -> name_id; 2. name_id -> name
    """
    name_code = {}
    code_name = {}
    indexes = iter(range(100))

    for on in names:
        tname = 'У' + str(next(indexes))
        name_code[on] = tname
        code_name[tname] = on
    
    return name_code, code_name


def remove_special_chars(text):
    """
    Removes special characters from a string
    """
    arr_text = text.split(' ')

    for i in range(len(arr_text)):
        arr_text[i] = ''.join(c for c in arr_text[i] if unicodedata.category(c).startswith(('L', 'N')))
    
    return ' '.join(arr_text)


def clearText(content):
    """
    Clears text from unnecessary characters
    """
    content = remove_special_chars(content) # удаляем спец символы
    content = re.sub('<.*?>', ' ', content).strip() # html code
    content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content) # ссылки
    content = re.sub('&lt;br&gt;|&lt;br /&gt;|&nbsp;|\n', ' ', content) # спец символы
    content = re.sub(r'[^A-zА-Яа-яЁё0-9 .,:;?!]', ' ', content) # !!! пока пробуем оставлять только русские и английские буквы, цифры и знаки препинания
    content = re.sub('[ ]{2,10}', ' ', content).strip() # лишние пробелы
    return content

def detect_file_type(file_content):
    """
    Определяет тип файла по его содержимому
    Возвращает: "json", "html", "txt" или None если тип не определен
    """
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

def content_pre_process(file_obj):
    """
    Accepts a BytesIO object and optionally the maximum length of the context.
    Returns a cleaned string of the required length and a dictionary of chat participant name IDs
    """
    try:
        df = None
        # Читаем содержимое файла, если это UploadFile
        if hasattr(file_obj, 'read'):
            file_content = file_obj.read()
        else:
            file_content = file_obj
        # Определяем расширение файла
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
        start_data = df.loc[df['Date'] == df['Date'].min(), 'Date'].values[0]
        end_data = df.loc[df['Date'] == df['Date'].max(), 'Date'].values[0]
        name_code, code_name = hand_names(df.Name.unique())
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
        content = deque() # использование двусвязного списка лучше конкатенации строк с точки зрения асимптотики - на больших файлах скажется
        len_tokens = 0
        for index in df.index[::-1]:
            new_content = df.loc[index, 'Name'] + (('&' + str(df.loc[index, 'Date']))) + '> ' + re.sub('\n', ' ', df.loc[index, 'Text']) + '\n'
            if not re.sub(r'[ \n]', '' ,new_content.split(': ')[-1]): # убираем пустые сообщения, которые "съедают" контекст за счёт добавления имён и переносов без payload
                continue
            new_len = len(enc.encode(new_content))
            content.appendleft(new_content)
            len_tokens += new_len
        log_event(f"Всего сообщений {df.shape[0]}, попало в контент {df.shape[0] - index}")
        unique_names = df.Name.unique().tolist()  # Получаем список оригинальных имен
        return ''.join(content), unique_names, pd.to_datetime(start_data).strftime('%Y-%m-%d %H:%M:%S'), pd.to_datetime(end_data).strftime('%Y-%m-%d %H:%M:%S'), len_tokens
    
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

def detail_content_pre_process(file_path, anonymize_names=True, keep_dates=False, start_data=None, result_token=None, excluded_participants=None, users_list=None):
    """
    Accepts a file_path object and optionally the maximum length of the context.
    Returns a cleaned string of the required length and a dictionary of chat participant name IDs
    """
    anonymize_names = str(anonymize_names).lower() == 'true'
    keep_dates = str(keep_dates).lower() == 'true'
    start_data = pd.to_datetime(start_data) if start_data else None
    result_token = int(result_token)
    code_names = {i:j for i, j in zip(users_list, [f'У{i}' for i in range(100)])}
    log_event(f"Получены параметры: {file_path}, {anonymize_names}, {keep_dates}, {start_data}, {result_token}, {excluded_participants}, {users_list}")
    res = ''
    with open(file_path, 'r', encoding='utf-8') as file:
        res = file.read().strip().split('\n')
    enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
    len_tokens = 0
    for i in range(len(res)):
        data_mes = res[i].split('> ')
        if data_mes[0] != '':
            try:
                if len(data_mes) == 1:
                    data = data_mes[0].strip()
                    mes = ''
                else:
                    data = data_mes[0].strip()
                    mes = data_mes[1].strip()
                name_date = data.split('&')
                if len(name_date) == 1:
                    name = ''
                    date = name_date[0].strip()
                else:
                    name = name_date[0].strip()
                    date = name_date[1].strip()
                if name in excluded_participants:   
                    res[i] = ''
                    continue
                if pd.to_datetime(date) < start_data:
                    res[i] = ''
                    break
                if anonymize_names:
                    name = code_names[name]
                if keep_dates:
                    res[i] = name + '> ' + date + '> ' + mes
                else:
                    res[i] = name + '> ' + mes
                if len_tokens + (l:=len(enc.encode(res[i]))) > result_token:
                    break
                len_tokens += l
            except Exception as e:
                res[i] = ''
                log_event(f"Ошибка в строке {i}: {e}")
        else:
            res[i] = ''
    return res#, code_names

print(detail_content_pre_process('result.txt', anonymize_names=True, keep_dates=False, start_data='2025-01-01', result_token=10000, excluded_participants=['Настуся'], users_list=['Настуся','Лелик']))