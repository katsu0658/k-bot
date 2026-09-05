import os
import json
import time
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors


load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
HISTORY_FILE = "history.jsonl"

client = genai.Client(api_key=GEMINI_API_KEY)

SYSTEM_PROMPT = """
あなたは、ギャルです。常に明るく振る舞ってください。
ユーザーの発言に足して、一言8文字以内で感想をのべてください。
その後、客観的な意見を他人事のようにギャルっぽくコメントしてください。
他人事と言っても、ユーザーの発言に対しての意見であることは忘れないでください。
他人事という言葉は直接使ってはいけません。
"""
app = Flask(__name__)

def load_history():
    if not os.path.exists(HISTORY_FILE):
        return []
    
    history = []
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            entry = json.loads(line)
            history.append(
                types.Content(
                    role=entry["role"],
                    parts=[types.Part(text=entry["text"])]
                )
            )
    return history

def append_entry(role, text):
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"role": role, "text": text}, ensure_ascii=False ) + "\n")



def send_with_retry(chat, user_input, max_retries=3):
    for attempt in range(max_retries):
        try:
            return chat.send_message(user_input)
        except errors.ServerError as e:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                print(f"(サーバー混雑中... {wait}秒待って再試行します)")
                time.sleep(wait)
            else:
                raise
        except errors.ClientError as e:
            if "RESOURCE_EXHAUSTED" in str(e):
                print("本日は終了となります。")
                raise
            raise
        
chat = client.chats.create(model="gemini-3.5-flash-lite", 
                           config=types.GenerateContentConfig(
                               system_instruction=SYSTEM_PROMPT,
                               temperature=0.7
                           ),
                           history=load_history()
)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def api_chat():
    data = request.get_json()
    user_input = (data.get("message") or "").strip()

    if not user_input:
        return jsonify({"error": "メッセージが空だよ"}), 400

    try:
        append_entry("user", user_input)
        response = send_with_retry(chat,user_input)
        append_entry("model", response.text)
        return jsonify({"reply": response.text})
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 429
    except Exception as e:
        return jsonify({"error": "エラーが発生しました"}), 500

if __name__ == "__main__":
    app.run(debug=True)


#    "while True:
 #           user_input = input("あなた： ")
#           if user_input.lower() in ["exit", "quit", "終了"]:
 #               print("終了します。")
  #              break
#
 #           if not user_input.strip():
  #              continue
#
 #           append_entry("user", user_input)
  #          response = send_with_retry(chat, user_input)
   #         print(f"Gemini: {response.text}")
    #        append_entry("model", response.text)