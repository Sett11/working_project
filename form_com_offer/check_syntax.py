import ast
import os

def check_syntax(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        ast.parse(content)
        return True, None
    except SyntaxError as e:
        return False, f'Строка {e.lineno}: {e.msg}'
    except Exception as e:
        return False, f'Ошибка чтения: {e}'

files_to_check = [
    'main.py',
    'db/database.py',
    'db/crud.py',
    'db/schemas.py',
    'back/back.py',
    'back/new_back.py',
    'db/models.py',
    'db/seeder.py',
    'front/new_front.py', 
    'front/front.py', 
    'front/auth_interface.py',
    'utils/compose_aircon_selector.py',
    'utils/compose_pdf_generator.py',
    'utils/auth.py',
    'utils/auth_middleware.py',
    'utils/mylogger.py',

]

for file_path in files_to_check:
    if os.path.exists(file_path):
        is_ok, error = check_syntax(file_path)
        if is_ok:
            print(f'✅ {file_path}: OK')
        else:
            print(f'❌ {file_path}: {error}')
    else:
        print(f'⚠️ {file_path}: файл не найден')
