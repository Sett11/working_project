import json
import pandas as pd
# from tqdm import tqdm

# есть повод оптимизировать, примерно 3 секунды 5 тыс строк
def readTGjson(filename, encoding='utf8'):
    # Read telegram's json and take only messages
    # Return DataFrame
    df = pd.DataFrame()
    # Exceptions during reading
    try:
        with open(filename, 'r', encoding=encoding) as f:
            jdata = json.load(f)
    except FileNotFoundError:
        print(f"Файл {filename} не найден.")
        return None
    except json.JSONDecodeError:
        print(f"Ошибка декодирования JSON в файле {filename}.")
        return None
    except UnicodeDecodeError:
        print(f"Ошибка декодирования файла {filename}. Проверьте кодировку.")
        return None
    except OSError as e:
        print(f"Ошибка при работе с файлом {filename}: {e}")
        return None

    for one in jdata['messages']:  # если простой формат сообщения
        if one['type'] != 'message': continue
        Name = one['from']
        Name_id = one['from_id']
        id_mess = one['id']

        dN = pd.to_datetime(one['date'],
                            format='%Y-%m-%dT%H:%M:%S')  # дату в более экономичный формат при конвертировании в строку

        if type(one['text']) == str:  # если там составной ответ из нескольких форматов
            Text = one['text']
        else:
            Text = ''
            for i in one['text']:
                if type(i) == str:
                    Text += f'{i} '
                else:
                    Text += f'{i["text"]} '

        df = pd.concat([df,
                        pd.DataFrame([{'id': id_mess, 'Date': dN, 'Name': Name, 'Name_id': Name_id, 'Text': Text.rstrip()}])],
                       ignore_index=True)
    return df