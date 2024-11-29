FROM python:3.12-slim
LABEL authors="Philippe Westenfelder"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONWARNINGS="ignore:Unverified HTTPS request"

CMD [ "python", "./core/main.py" ]

#ENTRYPOINT ["top", "-b"]