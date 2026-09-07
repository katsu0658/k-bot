const chatWindow = document.getElementById("chat-window");
const composer = document.getElementById("composer");
const input = document.getElementById("user-input");
const sendBtn = document.getElementById("send-btn");

let isSubmitting = false;

function addMessage(text, role) {
  const msg = document.createElement("div");
  msg.className = `msg msg-${role}`;

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;

  msg.appendChild(bubble);
  chatWindow.appendChild(msg);
  chatWindow.scrollTop = chatWindow.scrollHeight;
  return bubble;
}

function setFormDisabled(disabled) {
  isSubmitting = disabled;
  sendBtn.disabled = disabled;
  input.disabled = disabled;
}

composer.addEventListener("submit", async (e) => {
  e.preventDefault();
  
  const text = input.value.trim();
  if (!text || isSubmitting) return;

  // 1. ユーザーメッセージ描画とUIロック
  addMessage(text, "user");
  input.value = "";
  setFormDisabled(true);

  // 2. ローディングバブルの挿入
  const loadingBubble = addMessage("考え中...", "model loading");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });

    let data = {};
    const contentType = res.headers.get("content-type");
    if (contentType && contentType.includes("application/json")) {
      data = await res.json();
    }

    if (!res.ok) {
      loadingBubble.parentElement.className = "msg msg-error";
      loadingBubble.textContent = data.error || `エラーが発生しました (${res.status})`;
    } else {
      loadingBubble.textContent = data.reply;
      loadingBubble.parentElement.classList.remove("loading");
    }
  } catch (err) {
    loadingBubble.parentElement.className = "msg msg-error";
    loadingBubble.textContent = "通信に失敗しました。ネットワーク状況を確認してください。";
  } finally {
    setFormDisabled(false);
    input.focus();
    chatWindow.scrollTop = chatWindow.scrollHeight;
  }
});