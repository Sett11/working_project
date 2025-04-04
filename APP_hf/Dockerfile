FROM python:3.10-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 7861
EXPOSE 8000

CMD ["python", "front_and_back/front.py"]