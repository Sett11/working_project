from fastapi import FastAPI, Form, File, UploadFile
from hand_files import content_pre_process, detail_content_pre_process
import uvicorn
from logs import log_event as log_event_hf

def log_event(message):
    log_event_hf(f"FROM BACK: {message}")

app = FastAPI()

@app.post("/upload_file/")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_content = await file.read()
        text, participants, start_data, end_data, len_tokens = content_pre_process(file_content)
        if text is None:
            return {"error": "Error processing file"}
        return {
            "result": text,
            "participants": participants if participants else [],  # Список имён
            "start_data": start_data,
            "end_data": end_data,
            "len_tokens": len_tokens
        }
    except Exception as e:
        log_event(f"Error in upload_file: {str(e)}")
        return {"error": str(e)}
    
@app.post("/detail_processing_file/")
async def detail_processing_file(
    file: UploadFile = File(...),
    anonymize_names: str = Form(...),
    keep_dates: str = Form(...),
    start_data: str = Form(...),
    result_token: str = Form(...),
    excluded_participants: str = Form(...)
):
    """
    receives the request data and returns the result of the file handler
    """
    log_event(f"FROM BACK: Получены параметры: {file}, {anonymize_names}, {keep_dates}, {start_data}, {result_token}, {excluded_participants}")
    try:
        result_token = int(result_token)
        text, code_name = detail_content_pre_process(file.filename, anonymize_names, keep_dates, start_data, result_token, excluded_participants)
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