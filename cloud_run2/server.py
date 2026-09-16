import os
import json
import time
from flask import Flask, render_template, request, Response, jsonify
from google import genai
from google.genai import types

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

# Google Cloud Project & Location for Vertex AI / Agent Platform ADC
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "iceu-songpa10")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")

DEFAULT_MODEL = "gemini-3.8-flash"
SUPPORTED_MODELS = [
    {
        "id": "gemini-3.8-flash",
        "name": "Gemini 3.8 Flash",
        "tag": "Flash 3.8",
        "badge": "기본 모델 (ADC)",
        "description": "Google Model API 최신 플래그십 모델, 빠른 응답과 뛰어난 추론 능력",
        "isDefault": True
    },
    {
        "id": "gemini-3.7-flash",
        "name": "Gemini 3.7 Flash",
        "tag": "Flash 3.7",
        "badge": "고속 추론",
        "description": "효율적이고 빠른 멀티모달 플래그십 플래시 모델",
        "isDefault": False
    },
    {
        "id": "gemini-3-flash-preview",
        "name": "Gemini 3 Flash Preview",
        "tag": "Preview",
        "badge": "미리보기",
        "description": "차세대 추론 및 Agent Platform 실험 모델",
        "isDefault": False
    },
    {
        "id": "gemini-2.5-flash",
        "name": "Gemini 2.5 Flash",
        "tag": "Flash 2.5",
        "badge": "안정적 모델",
        "description": "안정적인 고효율 모델, 비용 효율적인 대화 지원",
        "isDefault": False
    }
]

def get_genai_client():
    """
    애플리케이션 기본 사용자 인증 정보(ADC) 기반으로 genai.Client를 초기화합니다.
    - Cloud Run 환경: Cloud Run에 바인딩된 서비스 계정의 ID 토큰을 자동으로 탐색하여 인증
    - 로컬 환경: `gcloud auth application-default login`으로 생성된 ADC 자격 증명 사용
    - 수동 API Key 설정이나 Secret Manager 마운트가 필요 없습니다.
    """
    return genai.Client(
        vertexai=True,
        project=PROJECT_ID,
        location=LOCATION
    )

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/favicon.ico")
def favicon():
    svg_icon = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="#7da0fa">'
        '<path d="M12 2L14.4 9.6L22 12L14.4 14.4L12 22L9.6 14.4L2 12L9.6 9.6L12 2Z"/>'
        '</svg>'
    )
    return Response(svg_icon, mimetype="image/svg+xml", headers={"Cache-Control": "public, max-age=86400"})

@app.route("/api/models", methods=["GET"])
def get_models():
    return jsonify({
        "models": SUPPORTED_MODELS,
        "default": DEFAULT_MODEL,
        "authMethod": "Application Default Credentials (ADC)",
        "adcConfigured": True,
        "project": PROJECT_ID,
        "location": LOCATION
    })

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "platform": "Google Cloud Run (ADC Mode)",
        "authMethod": "Application Default Credentials (ADC)",
        "project": PROJECT_ID,
        "location": LOCATION,
        "adcConfigured": True,
        "defaultModel": DEFAULT_MODEL
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    model = data.get("model", DEFAULT_MODEL)
    messages = data.get("messages", [])
    web_search = data.get("webSearch", True)

    if not messages:
        return jsonify({"error": "메시지가 비어 있습니다."}), 400

    # Ensure model is valid
    valid_ids = [m["id"] for m in SUPPORTED_MODELS]
    if model not in valid_ids:
        model = DEFAULT_MODEL

    # Format multi-turn context
    if len(messages) == 1:
        input_text = messages[0].get("content", "")
    else:
        history_lines = []
        for msg in messages[:-1]:
            role = "사용자" if msg.get("role") == "user" else "Gemini"
            history_lines.append(f"{role}: {msg.get('content', '')}")
        current_msg = messages[-1].get("content", "")
        input_text = f"이전 대화 기록:\n" + "\n".join(history_lines) + f"\n\n현재 사용자 질문:\n{current_msg}"

    def generate_stream():
        try:
            client = get_genai_client()

            final_prompt = (
                f"최신 정보나 사실 확인이 필요한 경우 구글 검색을 활용하여 정확하고 상세하게 한국어로 답변하세요.\n\n{input_text}"
                if web_search else input_text
            )

            # Generate content using Vertex AI / Agent Platform with ADC
            response = client.models.generate_content(
                model=model,
                contents=final_prompt,
                config=types.GenerateContentConfig(
                    temperature=1.0,
                    max_output_tokens=65536,
                    top_p=0.95,
                )
            )

            # Extract grounding metadata if search was used
            sources = []
            candidates = response.candidates or []
            if candidates:
                cand = candidates[0]
                metadata = getattr(cand, "grounding_metadata", None)
                if metadata:
                    chunks = getattr(metadata, "grounding_chunks", []) or []
                    for c in chunks:
                        web = getattr(c, "web", None)
                        if web:
                            uri = getattr(web, "uri", None)
                            title = getattr(web, "title", None) or uri
                            if uri:
                                sources.append({"title": title, "uri": uri})

            if sources:
                yield f"data: {json.dumps({'grounding': {'sources': sources, 'queries': []}}, ensure_ascii=False)}\n\n"

            # Stream response text smoothly
            full_text = response.text or ""
            chunk_size = 20
            for i in range(0, len(full_text), chunk_size):
                chunk = full_text[i:i + chunk_size]
                yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
                time.sleep(0.015)

            yield "data: [DONE]\n\n"

        except Exception as e:
            err_msg = f"Gemini ADC 호출 오류: {str(e)}"
            yield f"data: {json.dumps({'error': err_msg}, ensure_ascii=False)}\n\n"

    return Response(generate_stream(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[*] Cloud Run 2 (ADC 인증 모드) Gemini 챗봇 서버 시작: http://{host}:{port}")
    print(f"[*] 인증 방식: Application Default Credentials (ADC)")
    print(f"[*] 대상 프로젝트: {PROJECT_ID}, 리전: {LOCATION}")
    print(f"[*] 기본 모델: {DEFAULT_MODEL}")
    app.run(host=host, port=port, debug=False)
