# syntax=docker/dockerfile:1

FROM python:3.9

WORKDIR /SocketIO

COPY . .

RUN pip install -r requirements.txt

CMD ["python", "app.py"]