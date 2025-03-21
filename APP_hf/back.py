from fastapi import FastAPI, File, UploadFile, Form, Response
import re
from hand_files import content_pre_process
from delete_files import delete_files
import uvicorn

app = FastAPI()

delete_files('result.txt', 'app_logs.txt')

@app.post('/upload_file/')
async def upload_file(file: UploadFile = File(...), anonymize_names: bool = Form(...), save_datetime: bool = Form(...), max_len_context: int = Form(...)):
    dirty_path = file.headers.get('content-disposition')
    clean_path = dirty_path[re.search(r'filename\=.+', dirty_path).span()[0]:].replace('filename=','')[1:-1]
    text, _ = content_pre_process(clean_path, anonymize_names, save_datetime, max_len_context)
    
    if text is None:
        return {'error': 'Error processing file'}
    
    response = Response(content=text, media_type='text/plain')
    response.headers['Content-Disposition'] = f'attachment; filename=result.txt'
    return response

if __name__=='__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)