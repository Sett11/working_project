import pandas as pd
import re
from custom_print import custom_print
import io


def validate_txt(line):
    """
    Checking structure txt file
    """
    # Более гибкое регулярное выражение для проверки структуры
    return re.match(r'^\d{2}\.\d{2}\.\d{4}, \d{2}:\d{2} - [^:]+: .+$', line.strip()) is not None


def readWAtxt(filename, encoding='utf8'):
    """
    Read whatsApp's txt and take only messages
    Return DataFrame
    """
    df = pd.DataFrame()
    text = ''

    try:
        # Если filename это путь к файлу
        if isinstance(filename, str):
            with open(filename, 'r', encoding=encoding) as f:
                text = f.read()
        # Если filename это BytesIO объект
        elif isinstance(filename, io.BytesIO):
            text = filename.getvalue().decode(encoding)
        else:
            custom_print("Неподдерживаемый тип входных данных")
            return None
    except FileNotFoundError:
        custom_print(f"Файл {filename} не найден.")
        return None
    except UnicodeDecodeError:
        custom_print(f"Ошибка декодирования файла {filename}. Проверьте кодировку.")
        return None
    except OSError as e:
        custom_print(f"Ошибка при работе с файлом {filename}: {e}")
        return None

    if not text:
        custom_print("Файл пуст")
        return None
    
    # Разбиваем текст на сообщения, сохраняя первую строку
    text = re.split(r'\n(?=\d\d.\d\d.\d\d\d\d)', text)
    
    for one in text:
        # Пропускаем пустые строки и системные сообщения
        if not one.strip() or re.search('‎', one):
            continue

        mes = re.sub(r'\n', ' ', one).strip()

        if not validate_txt(mes):
            custom_print(f'Некорректная структура строки: {mes[:50]}...')
            continue
            
        try:
            tone = re.split(' - |: ', mes)
            if len(tone) < 3:
                custom_print(f'Некорректный формат сообщения: {mes[:50]}...')
                continue
                
            df = pd.concat([df,
                            pd.DataFrame([{'Date': pd.to_datetime(tone[0], format='%d.%m.%Y, %H:%M'), 
                                         'Name': tone[1],
                                         'Text': ' '.join(tone[2:]).strip()}])
                            ],
                           ignore_index=True)
        except Exception as e:
            custom_print(f'Ошибка при обработке строки: {str(e)}')
            continue

    if df.empty:
        custom_print("Не удалось извлечь сообщения из файла")
        return None

    return df