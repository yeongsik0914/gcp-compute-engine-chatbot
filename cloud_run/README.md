# ☁️ Google Cloud Run Gemini Chatbot (Serverless Container)

Google Cloud Platform의 완전 관리형 서버리스 컨테이너 플랫폼인 **Cloud Run**에 배포된 Gemini AI 웹 챗봇 서비스입니다.

---

## 🌟 주요 특징 및 장점

1. **Scale-to-Zero (비용 0원 최적화)**
   - 평상시 또는 사용자가 없을 때는 컨테이너 인스턴스가 0개로 축소되어 **컴퓨팅 비용이 0원**입니다.
   - 요청이 유입되는 순간 밀리초(ms) 단위로 컨테이너가 즉각 콜드스타트되어 대화를 처리합니다.
2. **구글 관리형 공식 HTTPS 기본 제공**
   - 별도의 Nginx 프록시나 Certbot Let's Encrypt 인증서 설치/갱신 없이 구글이 직접 발급하는 글로벌 TLS 인증서가 기본 적용됩니다 (`https://*.a.run.app`).
3. **완전 관리형 오토스케일링**
   - 트래픽이 폭증해도 별도의 로드밸런서 설정 없이 자동으로 수평 확장(Auto-scaling)됩니다.
4. **Secret Manager 네이티브 바인딩**
   - Cloud Run의 `--set-secrets` 옵션을 통해 Google Secret Manager에 저장된 `GEMINI_API_KEY`를 메모리 환경변수로 안전하게 주입합니다.
5. **SSE(Server-Sent Events) 실시간 스트리밍 지원**
   - Gunicorn 멀티스레드 워커(`--workers 1 --threads 8 --timeout 0`)를 통해 Gemini 3.8 Flash, 3.7 Flash 모델의 실시간 토큰 스트리밍과 Google Search Grounding 출처 링크를 지연 없이 전달합니다.

---

## 📂 디렉토리 구조

```
cloud_run/
├── Dockerfile              # Python 3.11 슬림 기반 컨테이너 명세
├── .dockerignore           # 컨테이너 빌드 제외 파일 설정
├── requirements.txt        # Flask, google-genai, gunicorn 의존성
├── server.py               # Cloud Run 포트($PORT) 지원 백엔드 서버
├── deploy_to_cloud_run.py  # gcloud CLI 원클릭 클라우드 빌드 및 배포 자동화
├── templates/
│   └── index.html          # Gemini 다크 테마 웹 UI
├── static/
│   ├── css/style.css       # 스타일시트
│   └── js/app.js           # 프론트엔드 인터랙션 로직
└── README.md               # Cloud Run 가이드 문서
```

---

## 🚀 배포 방법

### 1. `gcloud` CLI를 통한 원클릭 자동 배포
로컬에 Docker가 설치되어 있지 않아도 GCP Cloud Build가 클라우드 상에서 컨테이너를 자동 빌드하여 배포합니다:

```bash
cd cloud_run
python deploy_to_cloud_run.py
```

### 2. 수동 gcloud 명령어 배포
```bash
gcloud run deploy gemini-chatbot \
  --source . \
  --project=iceu-songpa10 \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-secrets=GEMINI_API_KEY=GEMINI_API_KEY:latest \
  --timeout=300 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3
```

---

## 💻 로컬 테스트 실행

```bash
cd cloud_run
python -m venv venv
venv\Scripts\activate      # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt

# 환경변수 설정 후 실행
$env:GEMINI_API_KEY="your-gemini-api-key"
python server.py
```
브라우저에서 `http://localhost:8080`으로 접속하여 테스트할 수 있습니다.
