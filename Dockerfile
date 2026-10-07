FROM python:3.12-slim
LABEL authors="Philippe Westenfelder"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WEB_HOST=0.0.0.0

# Web dashboard (only served when WEB_ENABLED=true)
EXPOSE 8080

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY core ./core

RUN useradd --create-home --uid 1000 bot \
    && mkdir data \
    && chown bot:bot data
USER bot

# Feature flags changed in the web dashboard are saved here
VOLUME ["/usr/src/app/data"]

CMD ["python", "-m", "core"]
