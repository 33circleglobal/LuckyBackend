FROM python:3.11-slim

WORKDIR /fast_app
COPY . /fast_app

RUN pip install fastapi uvicorn websockets

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]