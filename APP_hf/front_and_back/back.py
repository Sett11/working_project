from fastapi import FastAPI, Form, File, UploadFile
from hand_user_files.hand_files import content_pre_process
import uvicorn
from hand_logs.mylogger import Logger, LOG_FILE
import logging

logger = Logger('app_logger', LOG_FILE, level=logging.INFO)

def log_event(message):
    logger.info(f"FROM BACK: {message}")

app = FastAPI()

@app.post("/upload_file/")
async def upload_file(
    file: UploadFile = File(...), 
    anonymize_names: str = Form(...), 
    save_datetime: str = Form(...), 
    max_len_context: str = Form(...), 
    time_choise: str = Form(...)
):
    try:
        file_content = await file.read()
        text, code_name = content_pre_process(file_content, anonymize_names, save_datetime, max_len_context, time_choise)
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