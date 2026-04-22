FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app

RUN apt-get update && apt-get install -y xvfb && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install chromium

COPY server.py ./

ENV PORT=9191
ENV HEADLESS=false
ENV MAX_TIMEOUT=60000
ENV PROXY_URL=
ENV DISPLAY=:99

EXPOSE 9191

CMD xvfb-run --server-args="-screen 0 1920x1080x24" python server.py
