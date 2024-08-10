FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && \
    apt-get install -y unzip wget curl tzdata

# timezone
ENV TZ=America/Sao_Paulo
RUN echo "$TZ" > /etc/timezone && \
    ln -sf /usr/share/zoneinfo/$TZ /etc/localtime

COPY app/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN wget -O /tmp/chromedriver.zip https://chromedriver.storage.googleapis.com/$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE)/chromedriver_linux64.zip && \
    unzip /tmp/chromedriver.zip -d /usr/local/bin/ && \
    rm /tmp/chromedriver.zip

COPY app/ .

CMD ["python", "raspagem.py"]