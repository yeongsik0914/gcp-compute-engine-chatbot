import os
import sys
import json
import time
import datetime
import subprocess
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "deployment_log.md")

# GCP Cloud Run 2 Configuration (ADC Mode)
PROJECT_ID = "iceu-songpa10"
PROJECT_NUMBER = "920380215419"
REGION = "us-central1"
SERVICE_NAME = "gemini-chatbot-adc"
SERVICE_ACCOUNT = f"{PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

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
            cwd=SCRIPT_DIR,
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

def main():
    with open(LOG_FILE, "w", encoding="utf-8") as f:
        f.write("# GCP Cloud Run 2 (ADC 인증 모드) 배포 로그\n\n")
        f.write(f"- **배포 일시**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"- **GCP 프로젝트**: `{PROJECT_ID}` (Project Number: `{PROJECT_NUMBER}`)\n")
        f.write(f"- **타겟 리전**: `{REGION}`\n")
        f.write(f"- **서비스명**: `{SERVICE_NAME}`\n")
        f.write(f"- **인증 방식**: `Application Default Credentials (ADC)` (시크릿 키 불필요)\n")
        f.write(f"- **서비스 계정**: `{SERVICE_ACCOUNT}`\n\n---\n\n")

    log("=================================================================")
    log("GCP Cloud Run 2 (ADC 모드) 서버리스 컨테이너 빌드 및 배포 시작")
    log("=================================================================")

    # Step 1: 필수 GCP API 활성화 확인 (Agent Platform / Vertex AI)
    log("\n[단계 1/4] 필수 GCP 서비스 API 활성화 확인 (aiplatform, run, cloudbuild)")
    log_markdown("### 1. 필수 GCP API 활성화")
    enable_api_cmd = [
        "gcloud", "services", "enable",
        "aiplatform.googleapis.com",
        "run.googleapis.com",
        "cloudbuild.googleapis.com",
        "artifactregistry.googleapis.com",
        f"--project={PROJECT_ID}"
    ]
    run_cmd(enable_api_cmd, "Agent Platform & Cloud Run API 활성화")

    # Step 2: 서비스 계정에 Vertex AI 사용자 역할 바인딩
    log("\n[단계 2/4] 서비스 계정(ADC) 권한 확인 (roles/aiplatform.user)")
    log_markdown("### 2. 서비스 계정 IAM 권한 설정")
    iam_cmd = [
        "gcloud", "projects", "add-iam-policy-binding", PROJECT_ID,
        f"--member=serviceAccount:{SERVICE_ACCOUNT}",
        "--role=roles/aiplatform.user"
    ]
    run_cmd(iam_cmd, "Vertex AI User 역할 바인딩")

    # Step 3: Cloud Run 배포 (API Key 및 Secret Manager 옵션 없음!)
    log("\n[단계 3/4] Cloud Run 서비스 배포 (ADC 모드, 시크릿 키 불필요)")
    log_markdown("### 3. Cloud Run 배포 실행 (ADC)")
    deploy_cmd = [
        "gcloud", "run", "deploy", SERVICE_NAME,
        "--source=.",
        f"--project={PROJECT_ID}",
        f"--region={REGION}",
        "--platform=managed",
        "--allow-unauthenticated",
        f"--service-account={SERVICE_ACCOUNT}",
        "--set-env-vars=GOOGLE_CLOUD_PROJECT=iceu-songpa10,GOOGLE_CLOUD_LOCATION=global",
        "--timeout=300",
        "--memory=512Mi",
        "--cpu=1",
        "--min-instances=0",
        "--max-instances=3"
    ]
    dep_ok, dep_out = run_cmd(deploy_cmd, "Cloud Run 소스 기반 배포 (ADC)")
    if not dep_ok:
        log("[오류] Cloud Run 배포 실패!")
        return False

    # Step 4: 서비스 URL 확인 및 헬스체크
    log("\n[단계 4/4] Cloud Run 서비스 URL 조회 및 엔드투엔드 헬스체크")
    log_markdown("### 4. 서비스 URL 확인 및 헬스체크")
    url_cmd = [
        "gcloud", "run", "services", "describe", SERVICE_NAME,
        f"--project={PROJECT_ID}",
        f"--region={REGION}",
        "--format=value(status.url)"
    ]
    url_ok, service_url = run_cmd(url_cmd, "서비스 URL 조회")
    service_url = service_url.strip()

    if not url_ok or not service_url:
        log("[오류] 서비스 URL을 가져오지 못했습니다.")
        return False

    log(f"-> 획득한 Cloud Run 공식 HTTPS URL: {service_url}")

    health_url = f"{service_url}/api/health"
    models_url = f"{service_url}/api/models"

    max_retries = 10
    service_ready = False

    for attempt in range(1, max_retries + 1):
        time.sleep(3)
        log(f"헬스체크 시도 [{attempt}/{max_retries}]: {health_url}")
        try:
            req = urllib.request.Request(health_url, headers={"User-Agent": "CloudRunHealthCheck/1.0"})
            with urllib.request.urlopen(req, timeout=10) as res:
                if res.status == 200:
                    resp_body = res.read().decode("utf-8")
                    log(f"-> 헬스체크 성공! 응답: {resp_body}")
                    service_ready = True
                    break
        except Exception as e:
            log(f"-> 대기 중... ({str(e)})")

    if service_ready:
        log("\n=================================================================")
        log("🎉 Google Cloud Run 2 (ADC 인증 모드) 배포 완료!")
        log("=================================================================")
        log(f"🌐 공식 보안 HTTPS URL: {service_url}")
        log(f"🏷️ 서비스명: {SERVICE_NAME} (Region: {REGION})")
        log(f"🛡️ 인증 방식: Application Default Credentials (ADC) - 시크릿 키 관리 불필요")
        log(f"🔑 대상 서비스 계정: {SERVICE_ACCOUNT}")
        log(f"⚡ 스케일링 정책: Scale-to-Zero (min: 0, max: 3)")
        log("=================================================================")

        log_markdown(f"""
## 🎉 Cloud Run 2 (ADC) 배포 완료 요약

| 항목 | 상세 정보 |
| :--- | :--- |
| **서비스명** | `{SERVICE_NAME}` |
| **리전** | `{REGION}` |
| **공식 HTTPS 접속 주소** | **[{service_url}]({service_url})** |
| **인증 방식** | **Application Default Credentials (ADC)** (권장 표준) |
| **시크릿 관리** | **수동 키 관리 $0** (Cloud Run 서비스 계정 신원 자동 사용) |
| **백엔드 API** | Google Cloud Model API / Vertex AI (`aiplatform.googleapis.com`) |
| **지원 모델** | Gemini 3.8 Flash, Gemini 3.7 Flash, Gemini 3 Flash Preview, Gemini 2.5 Flash |
| **오토스케일링** | `0 ~ 3 인스턴스` (Scale-to-Zero 지원, 유휴 시 $0) |
""")
        return True
    else:
        log("[경고] 서비스 URL에 접근하는 데 시간이 걸릴 수 있습니다.")
        log(f"브라우저에서 직접 확인해 보세요: {service_url}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
