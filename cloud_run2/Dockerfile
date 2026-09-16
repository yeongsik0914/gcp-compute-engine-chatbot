# Python 3.11 슬림 공식 베이스 이미지
FROM python:3.11-slim

# 출력 버퍼 비활성화 및 기본 포트 설정
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Google Cloud Model API (Vertex AI ADC) 기본 위치 설정
ENV GOOGLE_CLOUD_PROJECT=iceu-songpa10
ENV GOOGLE_CLOUD_LOCATION=global

WORKDIR /app

# 의존성 설치 캐싱 최적화
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스코드 복사
COPY . .

# 8080 포트 노출
EXPOSE 8080

# Gunicorn WSGI 실행
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 server:app
