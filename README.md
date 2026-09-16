# 🤖 Google Gemini Web Chatbot (GCP Compute Engine 배포 및 HTTPS 보안 적용)

구글 Gemini 공식 웹 인터페이스([gemini.google.com](https://gemini.google.com/?hl=ko))의 감성적인 시그니처 다크 테마 디자인과 인터랙션을 구현하고, **Google Cloud Platform(GCP) Compute Engine**에 배포하여 **HTTPS 보안 암호화 통신**을 완벽하게 적용한 AI 챗봇 웹 서비스입니다.

---

## 🌐 서비스 접속 안내

| 구분 | 접속 URL | 설명 |
| :--- | :--- | :--- |
| **공식 보안 접속 (권장)** | **[https://34-45-106-67.sslip.io](https://34-45-106-67.sslip.io)** | Let's Encrypt 정식 CA 인증서 적용 (Chrome '주의 요함' 없는 안전한 자물쇠) |
| **포트 5000 지정 접속** | **[https://34-45-106-67.sslip.io:5000](https://34-45-106-67.sslip.io:5000)** | 기존 북마크 호환 포트 5000 HTTPS 암호화 서빙 |
| **대체 보안 접속** | **[https://34.45.106.67.sslip.io](https://34.45.106.67.sslip.io)** | 도메인 표기 대체 주소 |
| **일반 HTTP 접속** | `http://34-45-106-67.sslip.io` | 접속 시 HTTPS로 301 영구 이동(리다이렉트) 자동 처리 |

---

## 🔒 [핵심] HTTP에서 HTTPS로의 전환 및 적용 기술 분석

본 프로젝트는 초기에 Compute Engine 인스턴스의 공인 IP 및 포트 5000번(`http://34.45.106.67:5000`)을 통해 **HTTP(평문 통신)**로 서빙되었습니다. 그러나 웹 브라우저(Chrome/Edge)에서 **"주의 요함 (이 사이트는 보안 연결이 사용되지 않았습니다)"** 경고가 발생하며, 전송 데이터가 암호화되지 않는 보안 취약점이 있었습니다.

이를 해결하고 엔드투엔드 보안 암호화 통신을 구축하기 위해 다음과 같은 기술들이 도입 및 적용되었습니다:

```mermaid
graph TD
    subgraph "초기 HTTP 아키텍처 (평문 통신)"
        ClientA["웹 브라우저 (사용자)"] -->|"HTTP :5000 / :80 (평문 노출)"| Iptables["iptables NAT Redirection"]
        Iptables -->|"포트 포워딩 (80->5000)"| FlaskOld["Flask (0.0.0.0:5000)"]
        FlaskOld -->|"경고: 주의 요함 발생"| Warning["브라우저 보안 경고"]
    end

    subgraph "개선된 HTTPS 아키텍처 (SSL/TLS 보안 암호화)"
        ClientB["웹 브라우저 (Chrome)"] -->|"HTTPS :443 / :5000 (TLS 1.3 암호화)"| Nginx["Nginx Reverse Proxy"]
        ClientB -->|"HTTP :80 (평문 접속)"| Nginx
        Nginx -->|"301 Redirect (HTTP -> HTTPS)"| ClientB
        Nginx -->|"내부 루프백 프록시 (127.0.0.1:5001)"| FlaskNew["Flask Service (Gunicorn/Python)"]
        
        Certbot["Certbot & ACME Client"] -->|"Let's Encrypt CA 공인 인증서 자동 발급/갱신"| Nginx
        DNS["sslip.io Wildcard DNS"] -.->|"IP-도메인 1:1 매핑 (34.45.106.67)"| ClientB
        SecretMgr["GCP Secret Manager"] -->|"GEMINI_API_KEY 보안 주입"| FlaskNew
    end
```

### 🛠️ 프로토콜 전환을 위해 사용된 핵심 기술 및 구현 상세

#### 1. Nginx 리버스 프록시 (Reverse Proxy & TLS Termination)
- **도입 이유**: Flask 자체 내장 개발 서버는 단일 스레드 기반이거나 대규모 트래픽 및 정교한 SSL/TLS 핸드셰이크 처리에 취약합니다. 웹 서버의 표준인 Nginx를 프론트에 배치하여 TLS Termination(SSL 암호화 해제)을 전담하도록 구성했습니다.
- **포트 라우팅 및 호환성**:
  - **Port 80 (HTTP)**: HTTP로 유입되는 모든 트래픽을 안전한 HTTPS 주소(`https://$host$request_uri`)로 `301 Moved Permanently` 자동 리다이렉트합니다.
  - **Port 443 (HTTPS 표준)**: 최신 TLSv1.2 및 TLSv1.3 프로토콜과 강력한 암호화 알고리즘(`HIGH:!aNULL:!MD5`)을 적용하여 안전하게 서빙합니다.
  - **Port 5000 (HTTPS 호환)**: 기존 사용자나 북마크가 `:5000` 포트로 접속하더라도 SSL 에러 없이 정상적으로 HTTPS 대화가 이루어지도록 멀티 포트 SSL 리스닝을 구현했습니다.
- **실시간 스트리밍(SSE) 버퍼링 방지 최적화**:
  Gemini 모델의 실시간 토큰 스트리밍이 Nginx 프록시 버퍼에 갇혀 지연되지 않도록 전용 프록시 설정을 적용했습니다:
  ```nginx
  proxy_buffering off;
  proxy_cache off;
  proxy_set_header Connection '';
  proxy_http_version 1.1;
  chunked_transfer_encoding on;
  proxy_read_timeout 300s;
  ```

#### 2. Let's Encrypt 공인 인증 기관 (CA) 및 Certbot
- **도입 이유**: 자체 서명(Self-signed) 인증서는 통신 자체는 암호화하지만 브라우저에서 `NET::ERR_CERT_AUTHORITY_INVALID` 경고 화면을 띄워 사용자에게 신뢰를 주지 못합니다. 전 세계 브라우저가 신뢰하는 Let's Encrypt의 공인 CA 인증서를 적용했습니다.
- **ACME HTTP-01 챌린지 검증**:
  - Nginx에 `/.well-known/acme-challenge/` 전용 웹루트 디렉토리를 열어 Let's Encrypt 검증 서버가 인스턴스의 소유권을 자동으로 검증할 수 있도록 연동했습니다.
- **자동 갱신 데몬 (`certbot.timer`)**:
  - 90일 유효기간을 갖는 인증서가 만료 30일 전에 무중단으로 자동 갱신되도록 systemd 타이머를 등록하여 수동 관리 비용을 제거했습니다.

#### 3. 와일드카드 동적 DNS 매핑 서비스 (`sslip.io`)
- **도입 이유**: 일반적인 공인 IP 주소(Raw IPv4)는 무료 공인 CA 인증서 발급에 제약이 따르거나 상용 도메인 구매가 필요합니다.
- **해결 방식**: 인스턴스의 공인 IP(`34.45.106.67`)를 서브도메인으로 포함하는 `34-45-106-67.sslip.io`를 활용했습니다. `sslip.io` 네임서버는 해당 도메인 질의에 대해 자동으로 `34.45.106.67` IP를 반환하므로, 별도의 유료 도메인 등록 없이도 완전한 FQDN(Fully Qualified Domain Name)을 획득하고 Let's Encrypt 인증서를 정상 발급받을 수 있었습니다.

#### 4. GCP VPC 방화벽 규칙 (Firewall Rule Update)
- **설정 변경**: 기존 `allow-chatbot-port` 인바운드 방화벽 규칙에 HTTPS 표준 포트인 **`tcp:443`**을 추가 승인했습니다.
  ```bash
  gcloud compute firewall-rules update allow-chatbot-port \
      --allow=tcp:5000,tcp:80,tcp:443 \
      --project=iceu-songpa10
  ```

#### 5. 시스템 아키텍처 및 내부 네트워크 격리 (iptables & systemd)
- **기존 iptables NAT 리다이렉션 제거**: 초기에는 80번 포트를 5000번으로 단순 포워딩했으나, Nginx가 80번(HTTP 리다이렉트)과 443번(HTTPS 서빙)을 직접 제어해야 하므로 기존 커널 iptables 규칙을 정리했습니다:
  ```bash
  sudo iptables -t nat -D PREROUTING -p tcp --dport 80 -j REDIRECT --to-ports 5000
  ```
- **백엔드 포트 격리**: Flask 백엔드는 외부 인터넷에 직접 포트를 열지 않고, 내부 루프백인 `127.0.0.1:5001`에서만 수신하도록 분리하여 외부 직접 접근을 차단하고 보안 계층을 강화했습니다.

---

## 🌟 챗봇 주요 기능

1. **공식 Gemini UI 감성 완벽 재현**
   - 딥 다크 테마 (`#131314`) 및 은은한 중앙 블루 래디얼 글로우
   - `"10님, 시작해 볼까요?"` 중앙 환영 메시지 (클릭 시 사용자 이름 변경 가능)
   - 반응형 라운드 필(Pill) 프롬프트 입력창 및 부드러운 대화 렌더링
2. **최신 Gemini 모델 실시간 선택**
   - **Gemini 3.8 Flash** (`gemini-3.8-flash` - 기본값): 최신 플래그십 고속 멀티모달 모델
   - **Gemini 3.7 Flash** (`gemini-3.7-flash`): 고속 추론 및 지능형 멀티모달 모델
   - **Gemini 3 Flash Preview** (`gemini-3-flash-preview`): 차세대 추론 및 검색 모델
3. **Google Search Grounding (실시간 인터넷 검색)**
   - 최신 `google-genai` SDK 기반 실시간 웹 검색 도구(`tools=[{'type': 'google_search'}]`) 적용
   - 입력창의 **인터넷 검색 버튼(🌐)**으로 실시간 검색 ON/OFF 토글
   - 최신 뉴스, 날씨, 주가 등 실시간 정보 질의 시 검색 결과와 출처(Source 링크 카드)를 함께 시각화
4. **실시간 토큰 스트리밍 & 마크다운 뷰어**
   - Server-Sent Events (SSE) 기반 실시간 스트리밍
   - 코드 블록 구문 강조 및 원클릭 복사 버튼
   - 답변 텍스트 클립보드 복사 및 한국어 음성 재생(TTS)
5. **대화 히스토리 및 멀티모달 지원**
   - 좌측 슬라이드 사이드바를 통한 이전 대화 목록 저장 및 복원
   - 이미지 첨부(+) 및 음성 인식(Web Speech API) 지원

---

## 📂 프로젝트 파일 구조

```
gcp-compute-engine-chatbot/
├── compute_engine/                 # GCP Compute Engine 챗봇 및 VM 배포/보안 설정 패키지
│   ├── server.py                   # Flask 백엔드 서버 (Gemini API 호출 및 SSE 스트리밍)
│   ├── requirements.txt            # 파이썬 의존성 (flask, google-genai)
│   ├── deploy_to_gcp.py            # GCP Compute Engine 프로비저닝 자동화 스크립트
│   ├── startup_script.sh           # VM 시작 스크립트 (번들 압축 해제 및 systemd 서비스 등록)
│   ├── setup_https.sh              # VM 내 HTTPS/Nginx/Let's Encrypt 자동 구성 스크립트
│   ├── verify_https.py             # HTTPS 엔드포인트 및 리다이렉션 검증 스크립트
│   ├── compute_engine_example.ipynb # VM 프로비저닝 & Cloud Ops Agent 실습 노트북
│   ├── deployment_log.md           # 전체 배포 및 HTTPS 구성 상세 실행 로그
│   ├── templates/
│   │   └── index.html              # 시맨틱 마크업 웹 인터페이스
│   └── static/
│       ├── css/style.css           # Gemini 공식 다크 테마 바닐라 CSS
│       └── js/app.js               # SSE 클라이언트, 마크다운 파서, 모델/검색 UI 제어
├── cloud_run/                      # [NEW] GCP Cloud Run 서버리스 컨테이너 패키지
│   ├── Dockerfile                  # Python 3.11 슬림 기반 컨테이너 빌드 명세
│   ├── .dockerignore               # 빌드 제외 파일 설정
│   ├── requirements.txt            # 의존성 (flask, google-genai, gunicorn)
│   ├── server.py                   # Cloud Run 환경 ($PORT) 최적화 백엔드
│   ├── deploy_to_cloud_run.py      # Cloud Build 및 Cloud Run 원클릭 자동 배포 스크립트
│   ├── templates/index.html        # 웹 인터페이스 템플릿
│   ├── static/                     # CSS 및 JS 정적 에셋
│   └── README.md                   # Cloud Run 가이드 문서
├── .gitignore                      # Git 추적 제외 설정 (인증서, .env, venv 등)
└── README.md                       # 프로젝트 전체 기술 문서
```

---

## 🔐 GCP Secret Manager 보안 연동

API 키를 소스코드나 서버 설정 파일에 하드코딩하지 않고, 구글 클라우드의 Secret Manager로부터 안전하게 주입받도록 구성되었습니다:

- **사용된 시크릿 리소스**: `projects/920380215419/secrets/GEMINI_API_KEY`
- **IAM 권한 설정**: Compute Engine / Cloud Run 서비스 계정에 `roles/secretmanager.secretAccessor` 역할을 부여
- **Cloud Run 네이티브 연동**: `--set-secrets=GEMINI_API_KEY=GEMINI_API_KEY:latest` 플래그로 자동 주입

---

## 🚀 로컬 개발 및 실행 방법

### 1. `compute_engine` 또는 `cloud_run` 디렉토리 이동 및 가상환경 설정
```bash
cd cloud_run   # 또는 cd compute_engine

# 가상환경 생성
python -m venv venv

# 가상환경 활성화 (Windows)
venv\Scripts\activate
# 가상환경 활성화 (Linux/macOS)
source venv/bin/activate

# 의존성 패키지 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정 및 로컬 서버 실행
```bash
# Windows (PowerShell)
$env:GEMINI_API_KEY="your-gemini-api-key"
python server.py

# Linux / macOS
export GEMINI_API_KEY="your-gemini-api-key"
python server.py
```

웹 브라우저에서 `http://localhost:8080` (Cloud Run) 또는 `http://localhost:5000` (Compute Engine)으로 접속합니다.

---

## ☁️ 배포 옵션 1: Google Cloud Run 서버리스 배포 (권장: Scale-to-Zero, $0 유휴 비용)

로컬에 Docker 데스크톱이 없어도 GCP Cloud Build가 클라우드 상에서 컨테이너를 자동 빌드하여 안전하게 배포합니다:

```bash
cd cloud_run
python deploy_to_cloud_run.py
```

또는 수동 `gcloud` 명령어 실행:
```bash
gcloud run deploy gemini-chatbot \
  --source . \
  --project=iceu-songpa10 \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --set-secrets=GEMINI_API_KEY=projects/920380215419/secrets/GEMINI_API_KEY:latest \
  --timeout=300 \
  --memory=512Mi \
  --cpu=1 \
  --min-instances=0 \
  --max-instances=3
```

---

## 🖥️ 배포 옵션 2: GCP Compute Engine 가상머신 배포

`compute_engine/deploy_to_gcp.py`를 실행하면 VM 인스턴스 생성, 방화벽(5000, 80, 443) 개방, 소스코드 번들링 및 자동 배포가 원클릭으로 수행됩니다:

```bash
cd compute_engine
python deploy_to_gcp.py
```

---

## 🧪 검증 및 상태 확인

배포된 Compute Engine 인스턴스에 대해 다음 자동화 검증을 실행할 수 있습니다:

```bash
python compute_engine/verify_https.py
```

**검증 출력 결과**:
```text
=== HTTPS & Redirect Verification ===
[200] https://34-45-106-67.sslip.io -> OK (Served)
[200] https://34.45.106.67.sslip.io -> OK (Served)
[200] https://34-45-106-67.sslip.io:5000 -> OK (Served)
[301] http://34-45-106-67.sslip.io -> https://34-45-106-67.sslip.io/
[200] https://34-45-106-67.sslip.io/api/models -> OK (Served)
```
- **HTTPS 보안 자물쇠**: Chrome 브라우저에서 '주의 요함' 경고 없이 안전한 보안 연결 확인
- **실시간 스트리밍 대화**: `POST /api/chat` 요청 시 토큰 실시간 전송 및 Google Search Grounding 출처 링크 정상 반환 확인

---

## 🧹 GCP 자원 완벽 반납 및 익일 과금 방지 가이드 (Teardown & Cleanup)

실습이나 테스트를 마친 후 단순히 VM만 중지하거나 삭제할 경우, **사용자가 인지하지 못한 잔여 리소스가 백그라운드에서 계속 유료 과금을 유발**할 수 있습니다. 아래의 7대 점검 리스트와 명령어를 통해 모든 자원을 깨끗하게 반납할 수 있습니다.

### ⚠️ 사용자가 놓치기 쉬운 과금 유발 7대 잔여 자원

| 자원 종류 | 과금 발생 원인 | 반납 및 삭제 명령어 |
| :--- | :--- | :--- |
| **1. Compute VM 인스턴스** | 실행 중인 동안 vCPU 및 메모리 요금 지속 청구 | `gcloud compute instances delete <인스턴스명> --zone=<존> --quiet` |
| **2. 미연결 영구 디스크 (Unattached Disks)** | VM 삭제 시 부팅 디스크의 `auto-delete=no`였거나 추가 디스크가 남은 경우 **GB당 월간 스토리지 요금 계속 청구** | `gcloud compute disks list --filter="users:-"`<br>`gcloud compute disks delete <디스크명> --zone=<존> --quiet` |
| **3. 미사용 고정 공인 IP (Unused Static IPs)** | VM에 연결되지 않은 고정 IP는 **보유하고 있는 것만으로 시간당 유휴 요금 발생** | `gcloud compute addresses list --filter="status=RESERVED"`<br>`gcloud compute addresses delete <IP이름> --region=<리전> --quiet` |
| **4. 사용자 정의 방화벽 포트 (Firewall Rules)** | 개방된 포트(5000, 80, 443 등)가 남아 있을 경우 인바운드 보안 취약점 노출 | `gcloud compute firewall-rules delete allow-chatbot-port --quiet` |
| **5. 부하분산기 & 포워딩 규칙 (Forwarding Rules)** | 로드밸런서 및 포워딩 규칙이 남아 있을 경우 규칙당 기본 시간 요금 청구 | `gcloud compute forwarding-rules list`<br>`gcloud compute forwarding-rules delete <규칙명> --quiet` |
| **6. 스냅샷 및 커스텀 이미지 (Snapshots & Images)** | 백업/테스트 스냅샷의 용량 요금 | `gcloud compute snapshots list`<br>`gcloud compute snapshots delete <스냅샷명> --quiet` |
| **7. Cloud Ops Agent OS 정책 (Policy Assignments)** | VM 삭제 후 미사용 OS 설정 정책 정리 | `gcloud compute os-config os-policy-assignments delete goog-ops-agent-v2-template-1-7-0-us-central1-a --location=us-central1-a --quiet` |

### 🛠️ 일괄 상태 확인 원라이너 스크립트

터미널에서 아래 명령어를 실행하여 현재 프로젝트의 모든 잔여 자원 상태를 10초 만에 점검할 수 있습니다:

```bash
# 1. 실행 중인 VM 점검
gcloud compute instances list

# 2. 미연결 잔여 디스크 점검
gcloud compute disks list --filter="-users:*"

# 3. 미사용 유휴 고정 IP 점검
gcloud compute addresses list --filter="status=RESERVED"

# 4. 개방된 커스텀 방화벽 규칙 점검
gcloud compute firewall-rules list --filter="name:allow-chatbot-port"
```

> **💡 원클릭 자동 정리**:
> 주피터 노트북([compute_engine_example.ipynb](file:///e:/Project/gcp-compute-engine-chatbot/compute_engine_example.ipynb))의 **`## 9. GCP 자원 완벽 반납 및 익일 과금 방지 종합 정리 가이드`** 셀을 실행하면, 파이썬 기반으로 위 7대 자원을 한 번에 점검(`dry_run=True`)하거나 일괄 삭제/반납(`dry_run=False`)할 수 있습니다.

