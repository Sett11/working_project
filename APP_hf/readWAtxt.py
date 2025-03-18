import pandas as pd
import re

def validate_txt(line):
    return re.match(r'^\d{2}\.\d{2}\.\d{4}, \d{2}:\d{2} - [^:]+: .+$', line) is not None


def readWAtxt(filename):
    df = pd.DataFrame()

    try:
        text = ''
        with open(filename, 'r', encoding="utf8") as f:
            text = f.read()
    except FileNotFoundError:
        print(f"Файл {filename} не найден.")
    except UnicodeDecodeError:
        print(f"Ошибка декодирования файла {filename}. Проверьте кодировку.")
    except OSError as e:
        print(f"Ошибка при работе с файлом {filename}: {e}")

    if not text:
        return None
    
    text = text.splitlines()
    
    for one in text[1:]:  # пропустим системное сообщение

        if not validate_txt(one):
            print('Некорректная структура txt файла')
            return None
        
        tone = re.split(' - |: ', one)
        df = pd.concat([df,
                        pd.DataFrame([{'Date': pd.to_datetime(tone[0], format='%d.%m.%Y, %H:%M'), 'Name': tone[1],
                                       'Text': ' '.join(tone[2:]).strip()}])
                                       ],
                       ignore_index=True)

    return df