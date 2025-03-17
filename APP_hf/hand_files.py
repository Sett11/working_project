import unicodedata
import tiktoken #считает количество токенов
import readTGjson
import readWAtxt
import re

def remove_special_chars(text):
    #не всегда корректно обрабатываются хитрые имена, убираю спец символы
    arr_text = text.split(' ')
    for i in range(len(arr_text)):
        arr_text[i] = ''.join(c for c in arr_text[i] if unicodedata.category(c).startswith(('L', 'N')))
    return ' '.join(arr_text)

def clearText(content):
    # чистит текст от спец символов
    # вынести в библиотеку (Вот этот пункт не вполне понял. Добавить в re в виде отдельных функций?)
    # сюда можно добавить проверки и удаление персональной информации (Нужны примеры или более чёткие указания: что именно нужно проверить/удалить)
    content = re.sub('<.*?>', ' ', content).strip() #html code
    content = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', content) #ссылки
    content = re.sub('&lt;br&gt;|&lt;br /&gt;|&nbsp;|\n', ' ', content) #спец символы
    content = re.sub('[ ]{2,10}', ' ', content).strip() #личшние пробелы
    return content


def content_pre_process(filename, max_len=15200):
    # Вернет контент, почищенный и нужной длины и словарь преобразования обратно в имена
    try:
        if filename.split('.')[-1] == 'json':
            df = readTGjson.readTGjson(filename)  # Читаю файл и чищу его
        elif filename.split('.')[-1] == 'txt':
            df = readWAtxt.readWAtxt(filename)
        else:  # Если с другим расширением
            print('Не поддерживаемый формат')
            return None, None

        df['Name'] = df['Name'].apply(lambda x: remove_special_chars(x))
        df['Text'] = df['Text'].apply(lambda x: clearText(x))

        # Закодирую имена для экономии пространства
        name_code = {}
        code_name = {}
        for on in df.Name.unique():
            tname = 'У' + str(len(name_code))
            name_code[on] = tname
            code_name[tname] = on

        enc = tiktoken.encoding_for_model("gpt-3.5-turbo")

        content = ''
        len_tokens = 0
        for index in df.index[::-1]:  # Иду в обратном порядке
            new_content = name_code[df.loc[index, 'Name']] + ': ' + re.sub('\n', ' ', df.loc[index, 'Text']) + '\n'
            new_len = len(enc.encode(new_content))
            if new_len + len_tokens > max_len:
                break  # Если превысили длину
            content = new_content + content
            len_tokens += new_len

        print(f"Всего сообщений {df.shape[0]}, попало в контент {df.shape[0] - index}")
        return content, code_name

    except FileNotFoundError:
        print(f"Файл {filename} не найден.")
    except UnicodeDecodeError:
        print(f"Ошибка декодирования файла {filename}. Проверьте кодировку.")
    except ValueError as e:
        print(f"Ошибка преобразования данных: {e}")
    except KeyError as e:
        print(f"Ключ не найден в DataFrame: {e}")
    except TypeError as e:
        print(f"Ошибка типа данных: {e}")
    except Exception as e:
        print(f"Произошла ошибка: {e}")
    return None, None


print(content_pre_process('text.json')) # протестируем "руками" для начала)