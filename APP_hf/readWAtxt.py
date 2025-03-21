import pandas as pd
import re
from custom_print import custom_print


def validate_txt(line):
    """
    Checking structure txt file
    """
    return re.match(r'^\d{2}\.\d{2}\.\d{4}, \d{2}:\d{2} - [^:]+: .+$', line) is not None


def readWAtxt(filename, encoding='utf8'):
    """
    Read whatsApp's txt and take only messages
    Return DataFrame
    """
    df = pd.DataFrame()
    text = ''

    try:
        with open(filename, 'r', encoding=encoding) as f:
            text = f.read()
    except FileNotFoundError:
        custom_print(f"Файл {filename} не найден.")
    except UnicodeDecodeError:
        custom_print(f"Ошибка декодирования файла {filename}. Проверьте кодировку.")
    except OSError as e:
        custom_print(f"Ошибка при работе с файлом {filename}: {e}")

    if not text:
        return None
    
    text = re.split(r'\n(?=\d\d.\d\d.\d\d\d\d)', text)
    
    for one in text[1:]:
        
        if re.search('‎', one): # !!! пока такой вариант. Очень топорная валидация - нужно лучше)
            continue

        mes=re.sub(r'\n',' ',one)

        if not validate_txt(mes):
            print('Некорректная структура txt файла')
            return None
            
        tone = re.split(' - |: ', mes)
        df = pd.concat([df,
                        pd.DataFrame([{'Date': pd.to_datetime(tone[0], format='%d.%m.%Y, %H:%M'), 'Name': tone[1],
                                       'Text': ' '.join(tone[2:]).strip()}])
                                       ],
                       ignore_index=True)

    return df