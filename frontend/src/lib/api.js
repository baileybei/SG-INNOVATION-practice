const API_URL = "http://localhost:8000/chat/message";

export async function sendMessage({ userId, sessionId, text, image, audio }) {
  const form = new FormData();
  form.append("user_id", userId);

  if (sessionId) form.append("session_id", sessionId);
  if (text) form.append("text", text);
  if (image) form.append("image", image);
  if (audio) form.append("audio", audio, "recording.wav");

  const res = await fetch(API_URL, { method: "POST", body: form });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return res.json();
}
