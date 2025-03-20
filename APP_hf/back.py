from fastapi import FastAPI, File, UploadFile
from hand_files import content_pre_process
import uvicorn


app = FastAPI()

@app.post("/upload_file/")
async def upload_file(file: UploadFile = File(...)):
    print(file)
    result = content_pre_process(file)
    return {"result": result}


if __name__=='__main__':
    uvicorn.run(app, host="0.0.0.0", port=8000)