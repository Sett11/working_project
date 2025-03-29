from fastapi import FastAPI, File, UploadFile, Form, Response
from hand_files import content_pre_process
import uvicorn
import io
from custom_print import custom_print

app = FastAPI()


@app.post("/upload_file/")
async def upload_file(file: UploadFile = File(...), anonymize_names: bool = Form(...), save_datetime: bool = Form(...), max_len_context: int = Form(...), time_choise: str = Form(...)):
    """
    receives the request data and returns the result of the file handler
    """
    try:
        custom_print(f"Получен файл: {file.filename}")
        # Получаем содержимое файла
        file_content = await file.read()
        custom_print(f"Размер файла: {len(file_content)} байт")
        
        # Создаем временный файл в памяти
        file_obj = io.BytesIO(file_content)
        # Устанавливаем имя файла для BytesIO объекта
        file_obj.name = file.filename
        
        # Передаем BytesIO объект в обработчик
        text, code_name = content_pre_process(file_obj, anonymize_names, save_datetime, max_len_context, time_choise)
        
        if text is None:
            custom_print("Ошибка обработки файла: результат пустой")
            return {"error": "Error processing file"}
        
        custom_print("Файл успешно обработан\n") # добавляем перенос строки для разделения вывода в логе
        response = Response(content=text, media_type="text/plain")
        response.headers["Content-Disposition"] = f"attachment; filename=result.txt"
        return {"result": text, "code_name": code_name}
    except Exception as e:
        custom_print(f"Произошла ошибка: {str(e)}")
        return {"error": f"Error processing file: {str(e)}"}

if __name__=="__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)