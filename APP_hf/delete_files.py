import os
from custom_print import custom_print

def delete_files(*file_paths):
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                custom_print(f'Файл {file_path} удалён.')
        except Exception as e:
            custom_print(f'Ошибка удаления файла {file_path}: {e}')