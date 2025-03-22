from fastapi import FastAPI, File, UploadFile, Form, Response
import re
from hand_files import content_pre_process
from delete_files import delete_files
import uvicorn

app = FastAPI()


@app.post('/upload_file/')
async def upload_file(file: UploadFile = File(...), anonymize_names: bool = Form(...), save_datetime: bool = Form(...), max_len_context: int = Form(...), time_choise: str = Form(...)):
    """
    receives the request data and returns the result of the file handler
    """
    delete_files('result.txt', 'app_logs.txt') # удаляем старые файлы при загрузке нового файла
    
    dirty_path = file.headers.get('content-disposition')
    clean_path = dirty_path[re.search(r'filename\=.+', dirty_path).span()[0]:].replace('filename=','')[1:-1]
    text, _ = content_pre_process(clean_path, anonymize_names, save_datetime, max_len_context, time_choise)
    
    if text is None:
        return {'error': 'Error processing file'}
    
    response = Response(content=text, media_type='text/plain')
    response.headers['Content-Disposition'] = f'attachment; filename=result.txt'
    return response

if __name__=='__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)