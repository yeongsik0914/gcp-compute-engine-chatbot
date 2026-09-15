# Google Gemini Web Chatbot (Gemini 3.8 Flash & 3.7 Flash)

구글 Gemini 공식 웹 인터페이스(https://gemini.google.com/?hl=ko)의 시그니처 다크 테마 디자인과 레이아웃을 기반으로 구현된 고성능 AI 챗봇 애플리케이션입니다.

**Gemini 3.8 Flash**(기본값) 및 **Gemini 3.7 Flash** 모델을 실시간으로 선택하여 대화할 수 있으며, 서버의 환경변수(`GEMINI_API_KEY`)를 통해 API 키가 안전하게 관리됩니다.

---

## 🌟 주요 기능

1. **공식 Gemini UI 감성 재현**
   - 딥 다크 테마 (`#131314`) 및 은은한 중앙 블루 래디얼 글로우
   - `"10님, 시작해 볼까요?"` 중앙 환영 메시지 (이름 클릭 시 실시간 변경 가능)
   - 시그니처 라운드 필(Pill) 프롬프트 입력창 및 부드러운 대화 전환 애니메이션
2. **최신 Gemini 모델 지원 및 실시간 전환**
   - **Gemini 3.8 Flash** (`gemini-3.8-flash`): 최신 플래그십 고속 멀티모달 모델 (기본값)
   - **Gemini 3.7 Flash** (`gemini-3.7-flash`): 고속 추론 및 지능형 멀티모달 모델
   - **Gemini 3 Flash Preview** (`gemini-3-flash-preview`): 차세대 실시간 검색 프리뷰 모델
   - 프롬프트 입력창 우측 `Flash ∨` 드롭다운을 통해 즉시 모델 변경 가능
3. **Google Search Grounding (실시간 인터넷 검색 기능)**
   - 최신 `google-genai` SDK (`client.interactions.create`) 기반 Google Search 도구 (`tools=[{'type': 'google_search'}]`) 적용
   - 프롬프트 입력창의 **인터넷 검색 토글 버튼(🌐)**으로 실시간 검색 활성화/비활성화 가능
   - 답변 생성 시 실시간 웹 정보를 검색하여 오늘 날씨, 최신 뉴스 등 최신 정보 답변 제공
   - 참조한 웹사이트 출처(링크 및 언론사/도메인명)를 답변 하단에 카드 형태로 시각화
4. **실시간 스트리밍 (SSE) & 마크다운 렌더링**
   - Server-Sent Events (SSE) 기반 실시간 토큰 스트리밍
   - 제목, 볼드, 목록, 인라인 코드, 그리고 문법 강조 및 원클릭 복사 버튼이 포함된 코드 블록
   - 답변 텍스트 복사 및 한국어 음성 재생(TTS: Text-to-Speech)
5. **멀티모달 이미지 분석 & 음성 입력**
   - `+` 버튼 클릭 또는 드래그 앤 드롭으로 이미지 첨부 후 시각 분석 질의 가능
   - 마이크(🎤) 아이콘을 통한 실시간 한국어 음성 인식 (Web Speech API)
6. **대화 기록 관리**
   - 좌측 슬라이드 사이드바를 통해 이전 대화 목록 저장/불러오기/삭제 (로컬 스토리지 기반)

---

## 📂 프로젝트 구조

```
gcp-compute-engine-chatbot/
├── server.py              # Flask 백엔드 서버 (GEMINI_API_KEY 보안 프록시 및 SSE 스트리밍)
├── requirements.txt       # 파이썬 의존성 패키지 (flask>=3.0.0)
├── templates/
│   └── index.html         # Gemini 웹 인터페이스 마크업 (Semantic HTML5)
├── static/
│   ├── css/
│   │   └── style.css      # Gemini 다크 테마 바닐라 CSS 스타일시트
│   └── js/
│       └── app.js         # 대화 로직, SSE 파서, 마크다운 렌더러, 음성 및 멀티모달
└── README.md              # 프로젝트 문서 및 GCP 배포 가이드
```

---

## 🚀 로컬 실행 방법

### 1. 환경변수 설정
Gemini API 키를 환경변수로 등록합니다:

**Windows (PowerShell):**
```powershell
$env:GEMINI_API_KEY="your-gemini-api-key"
```

**Linux / macOS (Bash):**
```bash
export GEMINI_API_KEY="your-gemini-api-key"
```

### 2. 의존성 설치
```bash
pip install -r requirements.txt
```

### 3. 서버 실행
```bash
python server.py
```

브라우저에서 [http://localhost:5000](http://localhost:5000)으로 접속합니다.

---

## ☁️ GCP Compute Engine 배포 가이드

구글 클라우드 플랫폼(GCP)의 Compute Engine VM 인스턴스에 배포하는 절차입니다.

### 1. VM 인스턴스 생성
1. Google Cloud Console > **Compute Engine** > **VM 인스턴스** 이동
2. **인스턴스 만들기** 클릭:
   - OS: Ubuntu 22.04 LTS 또는 Debian 11/12 권장
   - 방화벽: **HTTP 트래픽 허용**, **HTTPS 트래픽 허용** 체크

### 2. 방화벽 규칙 설정 (5000번 포트 또는 80번 포트)
기본 5000번 포트를 외부에서 접속할 수 있도록 방화벽 규칙을 추가합니다:
```bash
gcloud compute firewall-rules create allow-chatbot-port \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:5000 \
    --source-ranges=0.0.0.0/0 \
    --target-tags=chatbot-server
```

### 3. 인스턴스 내 코드 클론 및 실행
SSH로 VM 인스턴스에 접속한 후:
```bash
# 필수 패키지 설치
sudo apt update && sudo apt install -y python3-pip git

# 프로젝트 복제
git clone https://github.com/<your-username>/gcp-compute-engine-chatbot.git
cd gcp-compute-engine-chatbot

# 패키지 설치
pip3 install -r requirements.txt

# 환경변수 등록 및 서버 실행
export GEMINI_API_KEY="your-api-key"
python3 server.py
```

### 4. systemd 서비스 등록 (백그라운드 지속 실행)
서버가 백그라운드에서 상시 구동되도록 systemd 서비스로 등록합니다:

`/etc/systemd/system/gemini-chatbot.service` 파일 생성:
```ini
[Unit]
Description=Gemini 3.8 Flash Chatbot Web App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/gcp-compute-engine-chatbot
Environment="GEMINI_API_KEY=your-api-key"
Environment="PORT=5000"
ExecStart=/usr/bin/python3 /home/ubuntu/gcp-compute-engine-chatbot/server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

서비스 활성화 및 시작:
```bash
sudo systemctl daemon-reload
sudo systemctl enable gemini-chatbot
sudo systemctl start gemini-chatbot
sudo systemctl status gemini-chatbot
```

이제 VM 인스턴스의 **외부 IP** (`http://<VM-EXTERNAL-IP>:5000`)로 접속하여 챗봇을 사용할 수 있습니다.
