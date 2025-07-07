from fastapi import FastAPI

app = FastAPI(title="API для автоматизации продаж")

@app.get("/")
def read_root():
    return {"message": "Бэкенд работает"}
