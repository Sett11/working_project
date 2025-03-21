import unicodedata
import tiktoken
from readWAtxt import readWAtxt
from readTGjson import readTGjson
from readTGhtml import readTGhtml
from custom_print import custom_print
import re
from collections import deque


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
    content = re.sub('<.*?>', ' ', content).strip() # html code
    content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content) # ссылки
    content = re.sub('&lt;br&gt;|&lt;br /&gt;|&nbsp;|\n', ' ', content) # спец символы
    content = re.sub(r'[^A-zА-Яа-яЁё0-9 .,:;?!]', ' ', content) # !!! пока пробуем оставлять только русские и английские буквы, цифры и знаки препинания
    content = re.sub('[ ]{2,10}', ' ', content).strip() # лишние пробелы
    return content


def content_pre_process(filename, anonymize_names, save_datetime, max_len_context):
    """
    Accepts a file name and optionally the maximum length of the context.
    Returns a cleaned string of the required length and a dictionary of chat participant name IDs
    """
    try:
        df = ''
        if filename.split('.')[-1] == 'json':
            df = readTGjson(filename)
        elif filename.split('.')[-1] == 'txt':
            df = readWAtxt(filename)
        elif filename.split('.')[-1] == 'html':
            df = readTGhtml(filename)
        else:
            custom_print('Не поддерживаемый формат')
            return None, None
        
        if df is None:
            custom_print(f'Ошибка обработки файла {filename}')
            return None, None
        
        df['Name'] = df['Name'].apply(lambda x: remove_special_chars(x))
        df['Text'] = df['Text'].apply(lambda x: clearText(x))

        name_code, code_name = hand_names(df.Name.unique())
        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
        content = deque() # использование двусвязного списка лучше конкатенации строк с точки зрения асимптотики - на больших файлах скажется
        len_tokens = 0

        for index in df.index[::-1]:
            new_content = name_code[df.loc[index, 'Name']] + ': ' + re.sub('\n', ' ', df.loc[index, 'Text']) + '\n'
            if not re.sub(r'[ \n]', '' ,new_content.split(': ')[1]): # убираем пустые сообщения, которые "съедают" контекст за счёт добавления имён и переносов без payload
                continue
            new_len = len(enc.encode(new_content))
            if new_len + len_tokens > max_len_context:
                break
            content.appendleft(new_content)
            len_tokens += new_len

        custom_print(f"Всего сообщений {df.shape[0]}, попало в контент {df.shape[0] - index}")
        return ''.join(content), code_name

    except FileNotFoundError:
        custom_print(f"Файл {filename} не найден.")
    except UnicodeDecodeError:
        custom_print(f"Ошибка декодирования файла {filename}. Проверьте кодировку.")
    except ValueError as e:
        custom_print(f"Ошибка преобразования данных: {e}")
    except KeyError as e:
        custom_print(f"Ключ не найден в DataFrame: {e}")
    except TypeError as e:
        custom_print(f"Ошибка типа данных: {e}")
    except Exception as e:
        custom_print(f"Произошла ошибка: {e}")
    return None, None