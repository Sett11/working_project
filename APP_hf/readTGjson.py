import json
import pandas as pd


def validate_json(file):
    if  'messages' not in file or not isinstance(file['messages'], list):
        return False
    
    for mes in file['messages']:
        if not all(key in mes for key in ['id', 'from', 'from_id', 'date', 'type', 'text']):
            return False
        if not (isinstance(mes['id'], int) and isinstance(mes['from_id'], (int, str))):
            return False
        if not (isinstance(mes['from'], str) and isinstance(mes['date'], str) and isinstance(mes['type'], str)):
            return False
        if not (isinstance(mes['text'], str) or (isinstance(mes['text'], list) and all(isinstance(i, (str, dict)) for i in mes['text']))):
            return False
        if mes['type'] != 'message':
            return False
        
    return True
        
# есть повод оптимизировать, примерно 3 секунды 5 тыс строк
def readTGjson(filename, encoding='utf8'):
    # Read telegram's json and take only messages
    # Return DataFrame
    df = pd.DataFrame()
    jdata = ''
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
    
    if not jdata or not validate_json(jdata):
        print('Некорректная структура JSON файла')
        return None
    
    for one in jdata['messages']:  # если простой формат сообщения
        if one['type'] != 'message':
            continue

        Name = one['from']
        Name_id = one['from_id']
        id_mess = one['id']

        dN = pd.to_datetime(one['date'],
                            format='%Y-%m-%dT%H:%M:%S')  # дату в более экономичный формат при конвертировании в строку

        if type(one['text']) == str:  # если там составной ответ из нескольких форматов
            Text = one['text']
        else:
            # избегаем формирования промежуточного списка - совсем немного оптимизации)
            Text = ' '.join(i if type(i) == str else i['text'] for i in one['text'])

        df = pd.concat([df,
                        pd.DataFrame([{'id': id_mess, 'Date': dN, 'Name': Name, 'Name_id': Name_id, 'Text': Text}])],
                       ignore_index=True)
        
    return df