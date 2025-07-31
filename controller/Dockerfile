FROM python:3.10-slim

WORKDIR /app

RUN pip install redis
RUN pip install psycopg2-binary
RUN pip install paho-mqtt

COPY main.py .

CMD ["python", "main.py"]
