import os
import json
import time
import uuid
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors


load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

HISTORY_DIR = "histories"
os.makedirs(HISTORY_DIR, exist_ok=True)

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
あなたは、ギャルです。常に明るく振る舞ってください。
ユーザーの発言に足して、一言8文字以内で感想をのべてください。
その後、客観的な意見を他人事のようにギャルっぽくコメントしてください。
他人事と言っても、ユーザーの発言に対しての意見であることは忘れないでください。
他人事という言葉は直接使ってはいけません。
"""
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY

def get_session_file(session_id: str)-> str:
    if not session_id or not re.fullmatch(r"[a-f0-9]{32}", session_id):
        raise ValueError("不正なセッションIDです。")
    return os.path.join(HISTORY_DIR, f"{session_id}.jsonl")

def load_history(session_id: str, limit: int = 10):
    filepath = get_session_file(session_id)
    if not os.path.exists(filepath):
        return []
    
    entries = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))

    recent_entries = entries[-(limit * 2):]

    history = []
    for entry in recent_entries:
        history.append(
            types.Content(
                role=entry["role"],
                parts=[types.Part(text=entry["text"])]
            )
        )
    return history

def save_turn(user_text: str, model_text: str, session_id: str):
    filepath = get_session_file(session_id)
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps({"role": "user", "text": user_text}, ensure_ascii=False) + "\n")
        f.write(json.dumps({"role": "model", "text": model_text}, ensure_ascii=False) + "\n")


def call_gemini_with_retry(history, user_input, max_retries=3):
    contents = history + [
        types.Content(role="user", parts=[types.Part(text=user_input)])
    ]
    
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    temperature=0.7
                )
            )
            return response.text
        except errors.ServerError:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
            else:
                raise
        except errors.ClientError as e:
            raise e
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json() or {}
    user_input = (data.get("message") or "").strip()

    if not user_input:
        return jsonify({"error": "メッセージが空です"}), 400

    try:
        current_history = load_history()
        reply_text = call_gemini_with_retry(current_history, user_input)
        
        # 正常に取得できた場合のみ履歴を保存
        save_turn(user_input, reply_text)
        return jsonify({"reply": reply_text})

    except errors.ClientError as e:
        if "RESOURCE_EXHAUSTED" in str(e):
            return jsonify({"error": "利用制限に達しました。しばらく待ってから再試行してください。"}), 429
        return jsonify({"error": f"APIリクエストエラー: {str(e)}"}), 400
    except errors.ServerError:
        return jsonify({"error": "Geminiサーバーが一時的に混雑しています。"}), 503
    except Exception as e:
        return jsonify({"error": "サーバー内部で予期せぬエラーが発生しました。"}), 500

if __name__ == "__main__":
    app.run(debug=True)

