import os
import json
import time
from flask import Flask, render_template, request, Response, jsonify
from google import genai

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, "templates"),
    static_folder=os.path.join(BASE_DIR, "static")
)

DEFAULT_MODEL = "gemini-3.8-flash"
SUPPORTED_MODELS = [
    {
        "id": "gemini-3.8-flash",
        "name": "Gemini 3.8 Flash",
        "tag": "Flash",
        "badge": "기본 모델",
        "description": "최신 고성능 멀티모달 모델, 빠른 응답과 뛰어난 추론 능력",
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
        "description": "실시간 Google Search Grounding 및 차세대 추론 모델",
        "isDefault": False
    }
]

def get_api_key():
    return os.environ.get("GEMINI_API_KEY", "").strip()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/models", methods=["GET"])
def get_models():
    return jsonify({
        "models": SUPPORTED_MODELS,
        "default": DEFAULT_MODEL,
        "apiKeyConfigured": bool(get_api_key())
    })

@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "platform": "Google Cloud Run",
        "apiKeyConfigured": bool(get_api_key()),
        "defaultModel": DEFAULT_MODEL
    })

@app.route("/api/chat", methods=["POST"])
def chat():
    api_key = get_api_key()
    if not api_key:
        return jsonify({"error": "GEMINI_API_KEY 환경변수가 설정되지 않았습니다. GCP Secret Manager 또는 환경변수를 확인해 주세요."}), 500

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

    model_target = f"models/{model}" if not model.startswith("models/") else model

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
            client = genai.Client(api_key=api_key)

            # Tools for Google Search
            tools = [{'type': 'google_search'}] if web_search else None

            generation_config = {
                'temperature': 1,
                'max_output_tokens': 65536,
                'top_p': 0.95,
                'thinking_level': 'high',
            }

            final_input = f"최신 정보나 사실 확인이 필요한 경우 구글 검색을 활용하여 정확하고 상세하게 한국어로 답변하세요.\n\n{input_text}" if web_search else input_text

            # Create interaction with Google GenAI SDK
            interaction = client.interactions.create(
                model=model_target,
                input=final_input,
                tools=tools,
                generation_config=generation_config,
            )

            # Retrieve citations from last step
            last_step = interaction.steps[-1] if hasattr(interaction, 'steps') and interaction.steps else None
            sources = []
            seen_urls = set()

            if last_step and hasattr(last_step, 'content') and last_step.content:
                for item in last_step.content:
                    annotations = getattr(item, 'annotations', None)
                    if annotations:
                        for ann in annotations:
                            url = getattr(ann, 'url', None)
                            title = getattr(ann, 'title', None) or url
                            if url and url not in seen_urls:
                                seen_urls.add(url)
                                sources.append({'title': title, 'uri': url})

            # Stream grounding citations
            if sources:
                yield f"data: {json.dumps({'grounding': {'sources': sources, 'queries': []}}, ensure_ascii=False)}\n\n"

            # Stream output text smoothly
            full_text = interaction.output_text or ""
            if not full_text and last_step and hasattr(last_step, 'content') and last_step.content:
                for item in last_step.content:
                    t = getattr(item, 'text', '')
                    if t:
                        full_text += t

            chunk_size = 20
            for i in range(0, len(full_text), chunk_size):
                chunk = full_text[i:i + chunk_size]
                yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
                time.sleep(0.015)

            yield "data: [DONE]\n\n"

        except Exception as e:
            err_msg = f"Gemini 검색 상호작용 오류: {str(e)}"
            yield f"data: {json.dumps({'error': err_msg}, ensure_ascii=False)}\n\n"

    return Response(generate_stream(), mimetype="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no"
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[*] Cloud Run Gemini Chatbot 서버 시작: http://{host}:{port}")
    print(f"[*] 기본 모델: {DEFAULT_MODEL}")
    print(f"[*] API Key 설정 상태: {'확인됨' if get_api_key() else '미설정(경고)'}")
    app.run(host=host, port=port, debug=False)
