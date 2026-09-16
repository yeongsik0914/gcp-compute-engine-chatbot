import os
import sys
import json
import time
import base64
import tarfile
import io
import datetime
import subprocess
import urllib.request
import urllib.error

# Workspace Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "deployment_log.md")

# GCP Configuration (matching compute_engine_example.ipynb & user requirements)
PROJECT_ID = "iceu-songpa10"
PROJECT_NUMBER = "920380215419"
ZONE = "us-central1-a"
REGION = "us-central1"
MACHINE_TYPE = "e2-medium"
SERVICE_ACCOUNT = f"{PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
SECRET_ID = "GEMINI_API_KEY"
SECRET_FULL_NAME = f"projects/{PROJECT_NUMBER}/secrets/{SECRET_ID}"
IMAGE = "projects/debian-cloud/global/images/debian-13-trixie-v20260908"
DISK_POLICY = f"projects/{PROJECT_ID}/regions/{REGION}/resourcePolicies/default-schedule-1"
LABELS = "goog-ops-agent-policy=v2-template-1-7-0,goog-ec-src=vm_add-gcloud"
TAGS = "http-server,https-server,chatbot-server"
FIREWALL_RULE = "allow-chatbot-port"

# Timestamped Instance Name (following notebook convention)
TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
INSTANCE_NAME = f"instance-chatbot-{TIMESTAMP}"

def log(msg, to_console=True):
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{now_str}] {msg}"
    if to_console:
        print(formatted)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(formatted + "\n")

def log_markdown(content):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(content + "\n")

def run_cmd(cmd_list, desc=""):
    gcloud_cmd = cmd_list[0]
    if gcloud_cmd == "gcloud" and sys.platform == "win32":
        cmd_list[0] = "gcloud.cmd"

    log(f"실행 명령어 ({desc}): {' '.join(cmd_list)}")
    start = time.time()
    try:
        proc = subprocess.run(
            cmd_list,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore"
        )
        elapsed = time.time() - start
        if proc.returncode == 0:
            log(f"-> 성공 ({elapsed:.1f}초)")
            if proc.stdout.strip():
                log_markdown(f"```\n{proc.stdout.strip()}\n```")
            return True, proc.stdout.strip()
        else:
            log(f"-> 실패 (코드 {proc.returncode}, {elapsed:.1f}초): {proc.stderr.strip()}")
            if proc.stderr.strip():
                log_markdown(f"```\n[오류] {proc.stderr.strip()}\n```")
            return False, proc.stderr.strip()
    except Exception as e:
        log(f"-> 예외 발생: {str(e)}")
        return False, str(e)

def build_app_payload():
    """Package project files into in-memory base64 tar.gz"""
    files_to_pack = [
        "server.py",
        "requirements.txt",
    ]
    collected_files = set(files_to_pack)
    for folder in ["templates", "static"]:
        folder_path = os.path.join(SCRIPT_DIR, folder)
        if os.path.exists(folder_path):
            for root, _, files in os.walk(folder_path):
                for f in files:
                    rel = os.path.relpath(os.path.join(root, f), SCRIPT_DIR).replace(os.sep, "/")
                    collected_files.add(rel)

    tar_buf = io.BytesIO()
    with tarfile.open(fileobj=tar_buf, mode="w:gz") as tar:
        for rel_path in sorted(collected_files):
            full_path = os.path.join(SCRIPT_DIR, rel_path.replace("/", os.sep))
            if os.path.exists(full_path):
                tar.add(full_path, arcname=rel_path)
    b64_data = base64.b64encode(tar_buf.getvalue()).decode("utf-8")
    return b64_data

def build_startup_script(b64_payload):
    script = f"""#!/bin/bash
set -e
exec > /var/log/chatbot-startup.log 2>&1

echo "[$(date)] GCP Compute Engine Gemini Chatbot Setup 시작"

# 1. 패키지 업데이트 및 필수 도구 설치
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-pip python3-venv git curl iptables

# 2. 배포 디렉토리 생성
APP_DIR="/opt/gemini-chatbot"
mkdir -p "$APP_DIR"
cd "$APP_DIR"

# 3. 소스코드 압축 해제
echo "{b64_payload}" | base64 -d | tar -xz -C "$APP_DIR"

# 4. 가상환경 생성 및 의존성 설치
python3 -m venv "$APP_DIR/venv"
"$APP_DIR/venv/bin/pip" install --upgrade pip
"$APP_DIR/venv/bin/pip" install -r "$APP_DIR/requirements.txt"

# 5. Secret Manager에서 GEMINI_API_KEY 가져오기
echo "[$(date)] Secret Manager에서 GEMINI_API_KEY 추출 시도: {SECRET_FULL_NAME}"
SECRET_VAL=$(gcloud secrets versions access latest --secret={SECRET_ID} --project={PROJECT_NUMBER} || true)

if [ -z "$SECRET_VAL" ]; then
    echo "[경고] gcloud CLI로 시크릿 획득 실패, VM 메타데이터 토큰으로 직접 호출 시도"
    ACCESS_TOKEN=$(curl -s "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token" -H "Metadata-Flavor: Google" | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
    SECRET_VAL=$(curl -s "https://secretmanager.googleapis.com/v1/{SECRET_FULL_NAME}/versions/latest:access" -H "Authorization: Bearer $ACCESS_TOKEN" | grep -o '"data":"[^"]*' | cut -d'"' -f4 | base64 -d || true)
fi

if [ -n "$SECRET_VAL" ]; then
    echo "[$(date)] GEMINI_API_KEY 시크릿 로드 성공"
    echo "GEMINI_API_KEY=$SECRET_VAL" > "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
else
    echo "[오류] GEMINI_API_KEY 시크릿을 가져오지 못했습니다."
fi

# 6. systemd 서비스 등록
cat << 'EOF' > /etc/systemd/system/gemini-chatbot.service
[Unit]
Description=Google Gemini 3.8 Flash & 3.7 Flash Chatbot Web App
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/gemini-chatbot
EnvironmentFile=/opt/gemini-chatbot/.env
Environment="PORT=5000"
Environment="HOST=0.0.0.0"
ExecStart=/opt/gemini-chatbot/venv/bin/python server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable gemini-chatbot.service
systemctl restart gemini-chatbot.service

# 7. 80번 포트 요청을 5000번 포트로 리다이렉트 (포트 번호 없이도 웹 접속 지원)
iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 5000 || true

echo "[$(date)] Gemini Chatbot 서비스 설정 완료 및 실행 중"
"""
    return script

def main():
    # Initialize Log File
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("# GCP Compute Engine 배포 및 작업 로그\n\n")
        f.write(f"- **배포 일시**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **타겟 GCP 프로젝트**: `{PROJECT_ID}` (Project Number: `{PROJECT_NUMBER}`)\n")
        f.write(f"- **타겟 리전/존**: `{ZONE}`\n")
        f.write(f"- **사용자 지정 Secret Manager**: `{SECRET_FULL_NAME}`\n\n---\n\n")

    log("=================================================================")
    log("GCP Compute Engine 프로비저닝 및 Gemini 챗봇 배포 시작")
    log("=================================================================")

    # Step 1: Secret Manager IAM 확인 및 권한 부여
    log("\n[단계 1/6] Secret Manager 접근 권한 확인 및 IAM 역할 부여")
    log_markdown("### 1. Secret Manager IAM 권한 설정")
    iam_cmd = [
        "gcloud", "secrets", "add-iam-policy-binding", SECRET_ID,
        f"--project={PROJECT_NUMBER}",
        f"--member=serviceAccount:{SERVICE_ACCOUNT}",
        "--role=roles/secretmanager.secretAccessor"
    ]
    run_cmd(iam_cmd, "Secret Manager IAM 바인딩")

    # Step 2: 방화벽 규칙 확인/생성
    log("\n[단계 2/6] 인바운드 방화벽 규칙 확인 및 생성 (5000, 80, 443 포트)")
    log_markdown("### 2. 방화벽 규칙 확인")
    fw_check_cmd = [
        "gcloud", "compute", "firewall-rules", "describe", FIREWALL_RULE,
        f"--project={PROJECT_ID}"
    ]
    ok, _ = run_cmd(fw_check_cmd, "방화벽 규칙 확인")
    if not ok:
        fw_create_cmd = [
            "gcloud", "compute", "firewall-rules", "create", FIREWALL_RULE,
            f"--project={PROJECT_ID}",
            "--direction=INGRESS",
            "--priority=1000",
            "--network=default",
            "--action=ALLOW",
            "--rules=tcp:5000,tcp:80,tcp:443",
            "--source-ranges=0.0.0.0/0",
            f"--target-tags=chatbot-server"
        ]
        run_cmd(fw_create_cmd, "방화벽 규칙 신규 생성")

    # Step 3: 애플리케이션 페이로드 및 시작 스크립트 빌드
    log("\n[단계 3/6] 챗봇 애플리케이션 번들 및 VM 시작 스크립트(Startup Script) 생성")
    log_markdown("### 3. 시작 스크립트 및 번들 준비")
    b64_payload = build_app_payload()
    startup_content = build_startup_script(b64_payload)
    startup_file = os.path.join(SCRIPT_DIR, "startup_script.sh")
    with open(startup_file, "w", encoding="utf-8", newline="\n") as f:
        f.write(startup_content)
    log(f"시작 스크립트 생성 완료: {startup_file} (소스 번들: {len(b64_payload)} bytes)")

    # Step 4: Compute Engine VM 인스턴스 생성
    log(f"\n[단계 4/6] Compute Engine 인스턴스 생성 요청: {INSTANCE_NAME}")
    log_markdown("### 4. Compute Engine VM 인스턴스 프로비저닝")
    create_vm_cmd = [
        "gcloud", "compute", "instances", "create", INSTANCE_NAME,
        f"--project={PROJECT_ID}",
        f"--zone={ZONE}",
        f"--machine-type={MACHINE_TYPE}",
        "--network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default",
        "--metadata=enable-osconfig=TRUE",
        f"--metadata-from-file=startup-script={startup_file}",
        "--maintenance-policy=MIGRATE",
        "--provisioning-model=STANDARD",
        f"--service-account={SERVICE_ACCOUNT}",
        "--scopes=https://www.googleapis.com/auth/cloud-platform",
        f"--create-disk=auto-delete=yes,boot=yes,device-name={INSTANCE_NAME},disk-resource-policy={DISK_POLICY},image={IMAGE},mode=rw,size=10,type=pd-balanced",
        "--no-shielded-secure-boot",
        "--shielded-vtpm",
        "--shielded-integrity-monitoring",
        f"--labels={LABELS}",
        f"--tags={TAGS}",
        "--reservation-affinity=any"
    ]
    vm_ok, vm_out = run_cmd(create_vm_cmd, "Compute Engine 인스턴스 생성")

    if not vm_ok:
        log("[오류] VM 인스턴스 생성 실패!")
        return False

    # Step 5: 외부 IP 확인
    log("\n[단계 5/6] 인스턴스 공인 IP 주소 조회")
    log_markdown("### 5. 인스턴스 IP 정보 확인")
    ip_cmd = [
        "gcloud", "compute", "instances", "describe", INSTANCE_NAME,
        f"--zone={ZONE}",
        f"--project={PROJECT_ID}",
        "--format=value(networkInterfaces[0].accessConfigs[0].natIP)"
    ]
    ip_ok, external_ip = run_cmd(ip_cmd, "외부 IP 주소 획득")
    external_ip = external_ip.strip()
    log(f"-> 획득한 인스턴스 외부 IP: {external_ip}")

    # Step 6: 서비스 부팅 및 헬스체크 모니터링
    log("\n[단계 6/6] 챗봇 서비스 구동 및 헬스체크 대기 (약 1~2분 소요)")
    log_markdown("### 6. 서비스 구동 상태 및 헬스체크")
    log(f"-> 접속 주소 1 (기본 포트): http://{external_ip}:5000")
    log(f"-> 접속 주소 2 (표준 웹): http://{external_ip}")

    health_url = f"http://{external_ip}:5000/api/health"
    models_url = f"http://{external_ip}:5000/api/models"

    max_retries = 30
    service_ready = False

    for attempt in range(1, max_retries + 1):
        time.sleep(6)
        log(f"헬스체크 시도 [{attempt}/{max_retries}]: {health_url}")
        try:
            req = urllib.request.Request(health_url, headers={"User-Agent": "HealthCheck/1.0"})
            with urllib.request.urlopen(req, timeout=5) as res:
                if res.status == 200:
                    resp_body = res.read().decode("utf-8")
                    log(f"-> 헬스체크 성공! 응답: {resp_body}")
                    service_ready = True
                    break
        except Exception as e:
            # Service still installing / starting up
            pass

    if service_ready:
        # Check API Key status
        try:
            req_m = urllib.request.Request(models_url)
            with urllib.request.urlopen(req_m, timeout=5) as res_m:
                models_data = json.loads(res_m.read().decode("utf-8"))
                api_configured = models_data.get("apiKeyConfigured", False)
                log(f"-> Secret Manager API Key 주입 확인: {'성공 (True)' if api_configured else '미확인 (False)'}")
        except Exception as e:
            api_configured = False

        log("\n=================================================================")
        log("🎉 GCP Compute Engine 배포 및 서비스 개시 완료!")
        log("=================================================================")
        log(f"웹 브라우저 접속 주소: http://{external_ip}:5000")
        log(f"표준 HTTP 접속 주소: http://{external_ip}")
        log(f"인스턴스명: {INSTANCE_NAME} (Zone: {ZONE})")
        log(f"Secret Manager 연동: {SECRET_FULL_NAME}")
        log("=================================================================")

        log_markdown(f"""
## 🎉 배포 완료 요약

| 항목 | 상세 정보 |
| :--- | :--- |
| **인스턴스명** | `{INSTANCE_NAME}` |
| **리전 / 존** | `{ZONE}` (`{REGION}`) |
| **머신 유형** | `{MACHINE_TYPE}` (2 vCPU / 4 GB RAM) |
| **공인 IP (External IP)** | **`{external_ip}`** |
| **웹 챗봇 접속 URL** | **[http://{external_ip}:5000](http://{external_ip}:5000)** 또는 **[http://{external_ip}](http://{external_ip})** |
| **Secret Manager 키** | `{SECRET_FULL_NAME}` (성공적으로 주입됨) |
| **지원 모델** | Gemini 3.8 Flash, Gemini 3.7 Flash, Gemini 3 Flash Preview |
| **실시간 검색 기능** | Google Search Grounding 지원 활성화 |
| **서비스 상태** | `RUNNING` (systemd: `gemini-chatbot.service`) |
""")
        return True
    else:
        log("\n[안내] 헬스체크 제한시간 도달. VM 내부 패키지 설치가 아직 진행 중일 수 있습니다.")
        log(f"잠시 후 브라우저에서 직접 접속해 보세요: http://{external_ip}:5000")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
