# 🛡️ Google Cloud Run 2 (Application Default Credentials - ADC 모드)

구글 클라우드 공식 권장 표준인 **애플리케이션 기본 사용자 인증 정보 (Application Default Credentials, ADC)** 방식을 기반으로 구현된 완전 관리형 Gemini AI 챗봇 서비스입니다.

---

## 💡 `cloud_run` vs `cloud_run2` 아키텍처 비교

| 비교 항목 | `cloud_run` (API Key / Secret Manager) | `cloud_run2` (ADC 모드 - 권장) ⭐ |
| :--- | :--- | :--- |
| **인증 방식** | API Key / Secret Manager (`GEMINI_API_KEY`) | **Application Default Credentials (ADC)** |
| **백엔드 서비스** | Gemini Developer API (`generativelanguage.googleapis.com`) | **Google Cloud Model API / Vertex AI (`aiplatform.googleapis.com`)** |
| **SDK 초기화** | `genai.Client(api_key=...)` | `genai.Client(vertexai=True, project=..., location='global')` |
| **키 관리 부담** | Secret Manager에 키 생성, IAM 바인딩, 회전 관리 필요 | **수동 키 관리 불필요 (보안 강화)** |
| **Cloud Run 배포** | `--set-secrets GEMINI_API_KEY=...` 필수 | **시크릿 바인딩 옵션 불필요 (`--set-secrets` 제거)** |
| **자격 증명 탐색** | 환경변수 직접 주입 | Cloud Run 환경의 서비스 계정 메타데이터 토큰 자동 획득 |

---

## 📂 디렉토리 구조

```
cloud_run2/
├── Dockerfile              # Python 3.11 슬림 컨테이너 빌드 명세
├── .dockerignore           # 컨테이너 빌드 제외 파일 설정
├── requirements.txt        # Flask, google-genai, gunicorn, google-auth
├── server.py               # ADC 기반 Google Model API 백엔드 서버
├── deploy_to_cloud_run.py  # ADC 모드 Cloud Run 원클릭 배포 자동화
├── templates/
│   └── index.html          # Gemini 공식 UI 웹 마크업 (ADC 뱃지 포함)
├── static/
│   ├── css/style.css       # 스타일시트
│   └── js/app.js           # 프론트엔드 인터랙션 로직
└── README.md               # ADC 가이드 문서
```

---

## 🚀 배포 방법

### 1. 자동화 스크립트 실행 (원클릭)
로컬에 Docker가 없어도 GCP Cloud Build가 컨테이너를 원격 빌드하여 배포합니다:

```bash
cd cloud_run2
python deploy_to_cloud_run.py
```

### 2. 수동 gcloud 명령어 배포
```bash
cd cloud_run2
gcloud run deploy gemini-chatbot-adc \
  --source . \
  --project=iceu-songpa10 \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --service-account=920380215419-compute@developer.gserviceaccount.com \
  --set-env-vars=GOOGLE_CLOUD_PROJECT=iceu-songpa10,GOOGLE_CLOUD_LOCATION=global \
  --timeout=300 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3
```

---

## 💻 로컬 테스트 실행

로컬 머신에서는 Google Cloud CLI의 ADC 로그인을 통해 동일한 방식으로 테스트할 수 있습니다:

```bash
# 1. 로컬 ADC 자격 증명 생성 (1회 실행)
gcloud auth application-default login
gcloud auth application-default set-quota-project iceu-songpa10

# 2. 가상환경 및 실행
cd cloud_run2
python -m venv venv
venv\Scripts\activate      # Linux/macOS: source venv/bin/activate
pip install -r requirements.txt

# 3. 별도의 API 키 설정 없이 서버 실행
python server.py
```

웹 브라우저에서 `http://localhost:8080`으로 접속하여 테스트합니다.
