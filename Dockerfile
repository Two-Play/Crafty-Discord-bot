FROM python:3.9-slim
LABEL authors="philippe"

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV USERNAME=""
ENV PASSWORD=""
ENV SERVER_URL=""
ENV DISCORD_TOKEN=""
ENV CRAFTY_TOKEN=""
ENV PYTHONWARNINGS="ignore:Unverified HTTPS request"

CMD [ "python", "./main.py" ]

#ENTRYPOINT ["top", "-b"]