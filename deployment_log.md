# GCP Compute Engine 배포 및 작업 로그

- **배포 일시**: 2026-09-15 15:01:22
- **타겟 GCP 프로젝트**: `iceu-songpa10` (Project Number: `920380215419`)
- **타겟 리전/존**: `us-central1-a`
- **사용자 지정 Secret Manager**: `projects/920380215419/secrets/GEMINI_API_KEY`

---

[2026-09-15 15:01:22] =================================================================
[2026-09-15 15:01:22] GCP Compute Engine 프로비저닝 및 Gemini 챗봇 배포 시작
[2026-09-15 15:01:22] =================================================================
[2026-09-15 15:01:22] 
[단계 1/6] Secret Manager 접근 권한 확인 및 IAM 역할 부여
### 1. Secret Manager IAM 권한 설정
[2026-09-15 15:01:22] 실행 명령어 (Secret Manager IAM 바인딩): gcloud.cmd secrets add-iam-policy-binding GEMINI_API_KEY --project=920380215419 --member=serviceAccount:920380215419-compute@developer.gserviceaccount.com --role=roles/secretmanager.secretAccessor
[2026-09-15 15:01:27] -> 성공 (4.7초)
```
bindings:
- members:
  - serviceAccount:920380215419-compute@developer.gserviceaccount.com
  role: roles/secretmanager.secretAccessor
etag: BwZbf0f7dL4=
version: 1
```
[2026-09-15 15:01:27] 
[단계 2/6] 인바운드 방화벽 규칙 확인 및 생성 (5000, 80 포트)
### 2. 방화벽 규칙 확인
[2026-09-15 15:01:27] 실행 명령어 (방화벽 규칙 확인): gcloud.cmd compute firewall-rules describe allow-chatbot-port --project=iceu-songpa10
[2026-09-15 15:01:32] -> 성공 (5.3초)
```
allowed:
- IPProtocol: tcp
  ports:
  - '5000'
- IPProtocol: tcp
  ports:
  - '80'
creationTimestamp: '2026-09-14T22:59:14.769-07:00'
description: ''
direction: INGRESS
disabled: false
id: '1631585042851782749'
kind: compute#firewall
logConfig:
  enable: false
name: allow-chatbot-port
network: https://www.googleapis.com/compute/v1/projects/iceu-songpa10/global/networks/default
priority: 1000
selfLink: https://www.googleapis.com/compute/v1/projects/iceu-songpa10/global/firewalls/allow-chatbot-port
sourceRanges:
- 0.0.0.0/0
targetTags:
- chatbot-server
```
[2026-09-15 15:01:32] 
[단계 3/6] 챗봇 애플리케이션 번들 및 VM 시작 스크립트(Startup Script) 생성
### 3. 시작 스크립트 및 번들 준비
[2026-09-15 15:01:32] 시작 스크립트 생성 완료: E:\Project\gcp-compute-engine-chatbot\startup_script.sh (소스 번들: 24508 bytes)
[2026-09-15 15:01:32] 
[단계 4/6] Compute Engine 인스턴스 생성 요청: instance-chatbot-20260915-150122
### 4. Compute Engine VM 인스턴스 프로비저닝
[2026-09-15 15:01:32] 실행 명령어 (Compute Engine 인스턴스 생성): gcloud.cmd compute instances create instance-chatbot-20260915-150122 --project=iceu-songpa10 --zone=us-central1-a --machine-type=e2-medium --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default --metadata=enable-osconfig=TRUE --metadata-from-file=startup-script=E:\Project\gcp-compute-engine-chatbot\startup_script.sh --maintenance-policy=MIGRATE --provisioning-model=STANDARD --service-account=920380215419-compute@developer.gserviceaccount.com --scopes=https://www.googleapis.com/auth/cloud-platform --create-disk=auto-delete=yes,boot=yes,device-name=instance-chatbot-20260915-150122,disk-resource-policy=projects/iceu-songpa10/regions/us-central1/resourcePolicies/default-schedule-1,image=projects/debian-cloud/global/images/debian-13-trixie-v20260908,mode=rw,size=10,type=pd-balanced --no-shielded-secure-boot --shielded-vtpm --shielded-integrity-monitoring --labels=goog-ops-agent-policy=v2-template-1-7-0,goog-ec-src=vm_add-gcloud --tags=http-server,https-server,chatbot-server --reservation-affinity=any
[2026-09-15 15:01:56] -> 성공 (24.2초)
```
NAME                              ZONE           MACHINE_TYPE  PREEMPTIBLE  INTERNAL_IP  EXTERNAL_IP   STATUS
instance-chatbot-20260915-150122  us-central1-a  e2-medium                  10.128.0.4   34.45.106.67  RUNNING
```
[2026-09-15 15:01:56] 
[단계 5/6] 인스턴스 공인 IP 주소 조회
### 5. 인스턴스 IP 정보 확인
[2026-09-15 15:01:56] 실행 명령어 (외부 IP 주소 획득): gcloud.cmd compute instances describe instance-chatbot-20260915-150122 --zone=us-central1-a --project=iceu-songpa10 --format=value(networkInterfaces[0].accessConfigs[0].natIP)
[2026-09-15 15:02:02] -> 성공 (5.2초)
```
34.45.106.67
```
[2026-09-15 15:02:02] -> 획득한 인스턴스 외부 IP: 34.45.106.67
[2026-09-15 15:02:02] 
[단계 6/6] 챗봇 서비스 구동 및 헬스체크 대기 (약 1~2분 소요)
### 6. 서비스 구동 상태 및 헬스체크
[2026-09-15 15:02:02] -> 접속 주소 1 (기본 포트): http://34.45.106.67:5000
[2026-09-15 15:02:02] -> 접속 주소 2 (표준 웹): http://34.45.106.67
[2026-09-15 15:02:08] 헬스체크 시도 [1/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:02:19] 헬스체크 시도 [2/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:02:28] 헬스체크 시도 [3/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:02:37] 헬스체크 시도 [4/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:02:46] 헬스체크 시도 [5/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:02:54] 헬스체크 시도 [6/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:03:03] 헬스체크 시도 [7/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:03:12] 헬스체크 시도 [8/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:03:21] 헬스체크 시도 [9/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:03:30] 헬스체크 시도 [10/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:03:39] 헬스체크 시도 [11/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:03:48] 헬스체크 시도 [12/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:03:57] 헬스체크 시도 [13/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:04:06] 헬스체크 시도 [14/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:04:15] 헬스체크 시도 [15/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:04:24] 헬스체크 시도 [16/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:04:33] 헬스체크 시도 [17/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:04:42] 헬스체크 시도 [18/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:04:51] 헬스체크 시도 [19/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:05:00] 헬스체크 시도 [20/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:05:09] 헬스체크 시도 [21/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:05:18] 헬스체크 시도 [22/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:05:26] 헬스체크 시도 [23/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:05:35] 헬스체크 시도 [24/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:05:44] 헬스체크 시도 [25/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:05:53] 헬스체크 시도 [26/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:06:02] 헬스체크 시도 [27/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:06:11] 헬스체크 시도 [28/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:06:20] 헬스체크 시도 [29/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:06:29] 헬스체크 시도 [30/30]: http://34.45.106.67:5000/api/health
[2026-09-15 15:06:32] [안내] VM 부팅 직후 데비안 백그라운드 apt-get lock으로 인해 시작 스크립트 대기 발생.
[2026-09-15 15:07:10] SSH 세션을 통한 직접 환경 구성 및 systemd 서비스 등록 실행:
- Python 가상환경 생성 (/opt/gemini-chatbot/venv)
- 패키지 설치: flask, google-genai
- GCP Secret Manager (`projects/920380215419/secrets/GEMINI_API_KEY`)로부터 API 키 추출 및 `/opt/gemini-chatbot/.env` 생성
- systemd 서비스 등록 및 활성화: `gemini-chatbot.service`
- 포트 80 -> 5000 리다이렉션 방화벽 iptables 규칙 적용

[2026-09-15 15:09:40] 서비스 활성화 상태 확인:
```
● gemini-chatbot.service - Gemini Chatbot Web Application
     Loaded: loaded (/etc/systemd/system/gemini-chatbot.service; enabled; preset: enabled)
     Active: active (running) since Tue 2026-09-15 06:09:12 UTC; 28s ago
   Main PID: 2174 (python)
      Tasks: 2 (limit: 4668)
     Memory: 41.7M ()
        CPU: 1.056s
     CGroup: /system.slice/gemini-chatbot.service
             └─2174 /opt/gemini-chatbot/venv/bin/python /opt/gemini-chatbot/server.py
```

### 7. 배포 검증 (Verification)
1. **모델 목록 및 API Key 구성 확인 (`GET /api/models`)**:
   - URL: `http://34.45.106.67:5000/api/models` 및 `http://34.45.106.67/api/models`
   - 응답: `HTTP 200 OK`, `apiKeyConfigured: True`
   - 로드된 모델: `gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3-flash-preview`

2. **실시간 스트리밍 대화 검증 (`POST /api/chat`)**:
   - 모델: `gemini-3-flash-preview`
   - 응답: Server-Sent Events (SSE) 정상 스트리밍 응답 완료 (HTTP 200 OK)

3. **Google Search Grounding 기능 검증**:
   - 질의: 2026년 최신 AI 소식 실시간 검색
   - 결과: Google Search Grounding 소스(yna.co.kr, investing.com 등) 정상 주입 및 최신 검색 결과 기반 답변 스트리밍 완료

=================================================================
[2026-09-15 15:22:00] GCP Compute Engine 인스턴스 배포 및 서비스 개시 완료
=================================================================
- **서비스 접속 URL (Port 5000)**: http://34.45.106.67:5000
- **웹 기본 접속 URL (Port 80)**: http://34.45.106.67
- **VM 인스턴스 이름**: `instance-chatbot-20260915-150122`
- **GCP 프로젝트**: `iceu-songpa10` (920380215419)
- **존(Zone)**: `us-central1-a`
- **Secret Manager 연동**: `projects/920380215419/secrets/GEMINI_API_KEY` (정상 주입 완료)

---

[2026-09-15 15:48:30] =================================================================
[2026-09-15 15:48:30] HTTPS(보안 연결, SSL/TLS) 적용 작업 시작
[2026-09-15 15:48:30] =================================================================

### 8. GCP 방화벽 규칙 포트 443(HTTPS) 추가
[2026-09-15 15:48:31] 실행 명령어: `gcloud.cmd compute firewall-rules update allow-chatbot-port --allow=tcp:5000,tcp:80,tcp:443 --project=iceu-songpa10`
[2026-09-15 15:48:58] -> 방화벽 업데이트 완료 (허용 포트: tcp:5000, tcp:80, tcp:443)

### 9. Nginx 리버스 프록시 및 Let's Encrypt 공인 SSL 인증서 발급
[2026-09-15 15:49:30] VM 환경 구성 실행:
1. 기존 iptables 포트 80 리다이렉션 규칙 제거
2. Flask 백엔드 서비스를 내부 전용 포트 5001(`127.0.0.1:5001`)로 격리 및 systemd 재시작
3. Nginx 및 Certbot 설치 (`apt-get install -y nginx certbot python3-certbot-nginx`)
4. Let's Encrypt 공식 공인 CA 인증서 발급 완료:
   - 인증서 도메인: `34-45-106-67.sslip.io`, `34.45.106.67.sslip.io`
   - 인증서 저장 경로: `/etc/letsencrypt/live/34-45-106-67.sslip.io/fullchain.pem`
   - 만료일: 2026-12-14 (자동 갱신 타이머 등록 완료)
5. Nginx 가상 호스트 설정 및 활성화:
   - 포트 80 (HTTP): `http://` 접속 시 `https://`로 301 자동 리다이렉트
   - 포트 443 (기본 HTTPS): SSL 적용 및 `http://127.0.0.1:5001` 리버스 프록시
   - 포트 5000 (HTTPS): 기존 북마크 호환을 위한 SSL 적용 및 리버스 프록시
   - 실시간 SSE 스트리밍 버퍼링 비활성화(`proxy_buffering off;`) 적용

### 10. HTTPS 서비스 검증 결과
1. **HTTPS 기본 접속 검증 (`https://34-45-106-67.sslip.io`)**:
   - `HTTP 200 OK` 정상 응답 (Let's Encrypt 공식 인증서 적용으로 Chrome 브라우저에서 '주의 요함' 경고 없이 안전한 자물쇠 표시)
2. **기존 포트 5000 HTTPS 접속 검증 (`https://34-45-106-67.sslip.io:5000`)**:
   - `HTTP 200 OK` 정상 응답
3. **HTTP -> HTTPS 자동 리다이렉트 검증 (`http://34-45-106-67.sslip.io`)**:
   - `HTTP 301 Moved Permanently` -> `https://34-45-106-67.sslip.io/` 리다이렉션 확인
4. **HTTPS 상에서의 실시간 대화 및 Google Search Grounding 검증**:
   - `POST https://34-45-106-67.sslip.io/api/chat`: Server-Sent Events 실시간 스트리밍 대화 정상 완료

=================================================================
[2026-09-15 15:55:00] HTTPS 보안 연결 전환 완료
=================================================================
- **공식 HTTPS 접속 URL (신뢰할 수 있는 보안 연결)**: **https://34-45-106-67.sslip.io**
- **기존 5000 포트 HTTPS 접속 URL**: **https://34-45-106-67.sslip.io:5000**
- **대체 HTTPS 접속 URL**: **https://34.45.106.67.sslip.io**
- **SSL 인증서**: Let's Encrypt 공식 CA 발급 완료 (자동 갱신 설정됨)

---

[2026-09-15 16:11:28] =================================================================
[2026-09-15 16:11:28] Compute Engine 인스턴스 자원 정리 및 삭제 시작
[2026-09-15 16:11:28] =================================================================
[2026-09-15 16:11:28] 실행 명령어: `gcloud.cmd compute instances delete instance-chatbot-20260915-150122 --zone=us-central1-a --project=iceu-songpa10 --quiet`
[2026-09-15 16:12:10] -> 인스턴스 및 부팅 디스크 삭제 완료: `instance-chatbot-20260915-150122`
[2026-09-15 16:12:25] 자원 정리 확인:
- `gcloud compute instances list`: 0 items (실행 중인 인스턴스 없음)
- `gcloud compute disks list`: 0 items (잔여 디스크 없음)
=================================================================
[2026-09-15 16:12:30] Compute Engine 인스턴스 전체 삭제 및 비용 발생 방지 완료
=================================================================

---

[2026-09-15 16:17:15] =================================================================
[2026-09-15 16:17:15] 공인 IP 및 포트 방화벽 규칙 반납/삭제
[2026-09-15 16:17:15] =================================================================
1. **공인 IP 반납 확인**:
   - `gcloud compute addresses list`: 0 items (임시 공인 IP 34.45.106.67은 VM 삭제와 동시에 GCP 풀로 자동 회수/반납 완료)
2. **포트 방화벽 규칙 삭제**:
   - 실행 명령어: `gcloud.cmd compute firewall-rules delete allow-chatbot-port --project=iceu-songpa10 --quiet`
   - 개방되었던 포트(5000, 80, 443)의 방화벽 규칙 `allow-chatbot-port` 삭제 완료
3. **네트워크 포워딩 규칙 확인**:
   - `gcloud compute forwarding-rules list`: 0 items
   - `gcloud compute target-pools list`: 0 items
=================================================================
[2026-09-15 16:18:30] 공인 IP, 포트 개방 방화벽 규칙, 네트워크 자원 전체 반납 완료
=================================================================

---

[2026-09-15 16:24:00] =================================================================
[2026-09-15 16:24:00] compute_engine_example.ipynb 및 README.md 자원 관리/반납 절차 통합 업데이트
[2026-09-15 16:24:00] =================================================================
1. **compute_engine_example.ipynb 업데이트**:
   - `## 8. Gemini 챗봇 서비스 배포 및 HTTPS(보안 연결) 자동 구성`: Secret Manager IAM, 방화벽 포트, Nginx/Let's Encrypt 자동화 셀 추가
   - `## 9. GCP 자원 완벽 반납 및 익일 과금 방지 종합 정리 가이드`:
     - 사용자가 인지하지 못할 수 있는 과금 유발 7대 잔여 자원(인스턴스, 미연결 디스크, 유휴 고정 IP, 방화벽, 포워딩 규칙, 스냅샷, OS 정책) 정의
     - 파이썬 기반 `audit_and_cleanup_all(dry_run=True/False)` 통합 함수 및 자동 점검/일괄 반납 셀 추가
2. **README.md 업데이트**:
   - `## 🧹 GCP 자원 완벽 반납 및 익일 과금 방지 가이드 (Teardown & Cleanup)` 섹션 신설
   - 과금 유발 7대 잔여 자원 리스트, 원인, gcloud CLI 반납 명령어 모음 및 원클릭 점검 원라이너 추가
=================================================================
[2026-09-15 16:25:00] 전체 자원 반납 절차 및 매뉴얼 업데이트 완료
=================================================================





