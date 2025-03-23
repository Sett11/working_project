import unicodedata
import tiktoken
import re
from collections import deque
import pandas as pd
import io
from readWAtxt import readWAtxt
from readTGjson import readTGjson
from readTGhtml import readTGhtml
from custom_print import custom_print


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


def content_pre_process(file_obj, anonymize_names=True, save_datetime=False, max_len_context=15200, time_choise=None):
    """
    Accepts a BytesIO object and optionally the maximum length of the context.
    Returns a cleaned string of the required length and a dictionary of chat participant name IDs
    """
    try:
        df = None
        # Определяем тип файла по расширению в объекте файла
        if isinstance(file_obj, io.BytesIO):
            filename = getattr(file_obj, 'name', '')
            custom_print(f"Обработка файла: {filename}")
            if filename.endswith('.json'):
                custom_print("Определен тип файла: JSON")
                df = readTGjson(file_obj)
            elif filename.endswith('.html'):
                custom_print("Определен тип файла: HTML")
                df = readTGhtml(file_obj)
            else:
                custom_print("Определен тип файла: TXT")
                df = readWAtxt(file_obj)
        else:
            custom_print('Ожидается объект BytesIO')
            return None, None
        
        if df is None or df.empty:
            custom_print('Не удалось прочитать файл')
            return None, None
            
        if 'Name' not in df.columns:
            custom_print('Файл не содержит необходимые колонки')
            return None, None
        
        custom_print(f"Успешно прочитан файл. Количество строк: {len(df)}")
        custom_print(f"Колонки в DataFrame: {df.columns.tolist()}")
        
        df['Name'] = df['Name'].apply(lambda x: remove_special_chars(x))
        df['Text'] = df['Text'].apply(lambda x: clearText(x))

        name_code, code_name = hand_names(df.Name.unique()) if anonymize_names else (None, None)
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
        content = deque() # использование двусвязного списка лучше конкатенации строк с точки зрения асимптотики - на больших файлах скажется
        len_tokens = 0
        date = pd.to_datetime(time_choise) if time_choise else None
        
        for index in df.index[::-1]:
            # если анонимизация установлена в True, то добавляем идентификатор имени к контенту, если нет - то просто имя
            # то же самое по сохранению даты/времени в контенте - добавляем к выводу, если установлено в True
            # на лету выбираем форматирование выходного контента - в зависимости от установленных пользователем параметров
            new_content = (name_code[df.loc[index, 'Name']] if anonymize_names else df.loc[index, 'Name']) +\
            (('&' + str(df.loc[index, 'Date'])) if save_datetime else '') +\
            (': ' if not save_datetime else '> ') + re.sub('\n', ' ', df.loc[index, 'Text']) + '\n'

            if not re.sub(r'[ \n]', '' ,new_content.split(': ')[-1]): # убираем пустые сообщения, которые "съедают" контекст за счёт добавления имён и переносов без payload
                continue

            new_len = len(enc.encode(new_content))
            if new_len + len_tokens > max_len_context or (date and date > df.loc[index, 'Date']): # если превышена установленная длина контекста или при итерации достигнута установленная дата начала отсчёта сообщений
                break
            content.appendleft(new_content)
            len_tokens += new_len

        custom_print(f"Всего сообщений {df.shape[0]}, попало в контент {df.shape[0] - index}")
        return ''.join(content), code_name

    except FileNotFoundError:
        custom_print(f"Файл не найден.")
    except UnicodeDecodeError:
        custom_print(f"Ошибка декодирования файла. Проверьте кодировку.")
    except ValueError as e:
        custom_print(f"Ошибка преобразования данных: {e}")
    except KeyError as e:
        custom_print(f"Ключ не найден в DataFrame: {e}")
    except TypeError as e:
        custom_print(f"Ошибка типа данных: {e}")
    except Exception as e:
        custom_print(f"Произошла ошибка: {e}")
    return None, None