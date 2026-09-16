# Python 3.11 슬림 공식 베이스 이미지
FROM python:3.11-slim

# 출력 버퍼 비활성화 (로그 즉시 출력) 및 기본 포트 설정
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# 의존성 설치 캐싱 최적화
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 애플리케이션 소스코드 복사
COPY . .

# 8080 포트 노출
EXPOSE 8080

# Cloud Run SSE 스트리밍 지원을 위한 Gunicorn WSGI 실행
# - workers: 1, threads: 8 (단일 컨테이너 인스턴스 동시성 지원)
# - timeout: 0 (SSE 실시간 토큰 스트리밍 타임아웃 차단 방지)
CMD exec gunicorn --bind 0.0.0.0:$PORT --workers 1 --threads 8 --timeout 0 server:app
