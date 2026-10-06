FROM python:3.12-slim
LABEL authors="Philippe Westenfelder"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY core ./core

RUN useradd --create-home --uid 1000 bot
USER bot

CMD ["python", "-m", "core"]
