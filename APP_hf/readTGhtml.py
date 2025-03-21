from bs4 import BeautifulSoup
import pandas as pd
from custom_print import custom_print


def validate_html(block):
    """
    Checking structure html file
    """
    return bool(block.find('div', class_ = 'from_name') and
                block.find('div', class_ = 'text') and
                block.find('div', class_ = 'pull_right date details'))


def readTGhtml(filename, encoding='utf8'):
    """
    Read telegram's html and take only messages
    Return DataFrame
    """
    df=pd.DataFrame()
    messages = ''

    try:
        with open(filename, encoding=encoding) as f:
            soup=BeautifulSoup(f, 'html.parser')

        messages = soup.find_all('div', class_ = 'message default clearfix')

    except FileNotFoundError:
        custom_print(f'Файл {filename} не найден')
    except UnicodeDecodeError:
        custom_print(f'Ошибка декодирования файла {filename}. Проверьте кодировку.')
    except OSError as e:
        custom_print(f'Ошибка при работе с файлом {filename}: {e}')

    if not messages:
        return None

    for mes in messages:

        if not validate_html(mes): # можно или прекращать обработку файла или переходить к следующему блоку. Второе предпочтительнее, что видно на примере messages.html
            # custom_print(f'Некорректная структура файла {filename}')
            # return None
            continue
        
        date = mes.find('div', class_ = 'pull_right date details').text.strip()
        name = mes.find('div', class_ = 'from_name').text.strip()
        text = mes.find('div', class_ = 'text').text.strip()

        df = pd.concat([df,
                        pd.DataFrame([{'Date': pd.to_datetime(date), 'Name': name, 'Text': text}])],
                        ignore_index=True)
        
    return df