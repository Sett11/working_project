from fastapi import FastAPI, Form, File, UploadFile
from hand_files import content_pre_process, detail_content_pre_process
import uvicorn
from logs import log_event as log_event_hf

def log_event(message):
    log_event_hf(f"FROM BACK: {message}")

app = FastAPI()

@app.post("/upload_file/")
async def upload_file(
    file: UploadFile = File(...)):
    """
    receives the request data and returns the result of the file handler
    """
    try:
        # Сначала читаем файл асинхронно
        file_content = await file.read()
        text, code_name, start_data, end_data, len_tokens = content_pre_process(file_content)
        if text is None:
            log_event("Ошибка обработки файла: результат пустой")
            return {"error": "Error processing file"}
        log_event(f"Файл успешно обработан: {text[:100]}, {code_name}, {start_data}, {end_data}, {len_tokens}")
        return {
            "result": text,
            "code_name": code_name,
            "start_data": start_data,
            "end_data": end_data,
            "len_tokens": len_tokens
        }
    except Exception as e:
        log_event(f"FROM BACK: Произошла ошибка: {str(e)}")
        return {"error": f"Error processing file: {str(e)}"}
    
@app.post("/detail_processing_file/")
async def detail_processing_file(
    file: UploadFile = File(...),
    anonymize_names: str = Form(...),
    start_data: str = Form(...),
    result_token: str = Form(...),
    excluded_participants: str = Form(...)
):
    """
    receives the request data and returns the result of the file handler
    """
    try:
        file_content = await file.read()
        text, code_name = detail_content_pre_process(file_content, anonymize_names, start_data, result_token, excluded_participants)
        if text is None:
            log_event("Ошибка обработки файла: результат пустой")
            return {"error": "Error processing file"}   
        log_event("Файл успешно обработан\n")
        return {
            "result": text,
            "code_name": code_name
        }
    except Exception as e:  
        log_event(f"FROM BACK: Произошла ошибка: {str(e)}")
        return {"error": f"Error processing file: {str(e)}"}

if __name__=="__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)