from bs4 import BeautifulSoup
import pandas as pd
from custom_print import custom_print
import io


def validate_html(block):
    """
    Checking structure html file
    """
    try:
        has_name = bool(block.find('div', class_='from_name'))
        has_text = bool(block.find('div', class_='text'))
        has_date = bool(block.find('div', class_='pull_right date details'))
        
        if not has_name or not has_text or not has_date:
            custom_print(f"Блок сообщения не содержит все необходимые элементы: name={has_name}, text={has_text}, date={has_date}")
            return False
        return True
    except Exception as e:
        custom_print(f"Ошибка при валидации HTML блока: {str(e)}")
        return False


def readTGhtml(filename, encoding='utf8'):
    """
    Read telegram's html and take only messages
    Return DataFrame
    """
    df = pd.DataFrame()
    messages = None

    try:
        # Если filename это путь к файлу
        if isinstance(filename, str):
            custom_print(f"Чтение файла по пути: {filename}")
            with open(filename, encoding=encoding) as f:
                content = f.read()
                if not content.strip():
                    custom_print("Файл пустой")
                    return None
                custom_print(f"Содержимое файла начинается с: {content[:200]}")
                soup = BeautifulSoup(content, 'html.parser')
        # Если filename это BytesIO объект
        elif isinstance(filename, io.BytesIO):
            custom_print("Чтение файла из BytesIO объекта")
            content = filename.getvalue().decode(encoding)
            if not content.strip():
                custom_print("Файл пустой")
                return None
            custom_print(f"Содержимое файла начинается с: {content[:200]}")
            soup = BeautifulSoup(content, 'html.parser')
        else:
            custom_print("Неподдерживаемый тип входных данных")
            return None

        custom_print("Поиск сообщений в HTML...")
        messages = soup.find_all('div', class_='message default clearfix')
        custom_print(f"Найдено сообщений: {len(messages)}")
        
        if not messages:
            custom_print("Не найдено сообщений в файле")
            return None

    except FileNotFoundError:
        custom_print('Файл не найден')
        return None
    except UnicodeDecodeError:
        custom_print('Ошибка декодирования файла. Проверьте кодировку.')
        return None
    except OSError as e:
        custom_print(f'Ошибка при работе с файлом: {e}')
        return None
    except Exception as e:
        custom_print(f'Неожиданная ошибка при чтении файла: {e}')
        return None

    valid_messages = []
    for i, mes in enumerate(messages):
        custom_print(f"Обработка сообщения {i+1} из {len(messages)}")
        if not validate_html(mes):
            continue
        
        try:
            date = mes.find('div', class_='pull_right date details').text.strip()
            name = mes.find('div', class_='from_name').text.strip()
            text = mes.find('div', class_='text').text.strip()
            
            if not date or not name or not text:
                custom_print("Пропущено сообщение с пустыми полями")
                continue
                
            valid_messages.append({
                'Date': pd.to_datetime(date),
                'Name': name,
                'Text': text
            })
        except Exception as e:
            custom_print(f"Ошибка при обработке сообщения: {str(e)}")
            continue
    
    if not valid_messages:
        custom_print("Не удалось извлечь корректные сообщения из файла")
        return None
        
    df = pd.DataFrame(valid_messages)
    custom_print(f"Успешно обработано {len(valid_messages)} сообщений")
    return df