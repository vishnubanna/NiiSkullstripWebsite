#python:3.7
FROM python:3.7-slim

RUN apt-get update -y
RUN apt-get install -y python-pip python-dev build-essential

# copy current location to app
COPY . /app 
WORKDIR /app

RUN ls

RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install gunicorn

ENV PORT 8080

# ENTRYPOINT ["python"]
# CMD ["src/mainAPI2.py"]

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 src.mainAPI2:app
