# Chat Frontend Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a React (Next.js) chat page that faithfully reproduces the Figma design and connects to the existing FastAPI `POST /chat/message` backend.

**Architecture:** Next.js App Router with Tailwind CSS. Single `/chat` route with 6 components: TopBar, MessageList, MessageBubble, InputBar, ActionSheet, ImagePreview. State managed via `useState` in the chat page; API calls via `fetch` + `FormData`.

**Tech Stack:** Next.js 14, Tailwind CSS, MediaRecorder API, fetch

---

## File Map

| File | Responsibility |
|------|---------------|
| `frontend/package.json` | Dependencies: next, react, tailwindcss |
| `frontend/next.config.js` | Next.js config |
| `frontend/tailwind.config.js` | Custom colors from Figma design tokens |
| `frontend/postcss.config.js` | PostCSS for Tailwind |
| `frontend/src/app/layout.js` | Global layout — 393px mobile frame, centered |
| `frontend/src/app/globals.css` | Tailwind directives + custom styles |
| `frontend/src/app/page.js` | Root redirect to `/chat` |
| `frontend/src/app/chat/page.js` | Chat page — all state, API calls, orchestration |
| `frontend/src/components/TopBar.js` | "Chat" title + agent icon + hamburger menu |
| `frontend/src/components/MessageList.js` | Scrollable message area + auto-scroll |
| `frontend/src/components/MessageBubble.js` | Single bubble (text and/or image) |
| `frontend/src/components/InputBar.js` | Text input + mic + upload button |
| `frontend/src/components/ActionSheet.js` | Bottom sheet: Camera / Gallery / Cancel |
| `frontend/src/components/ImagePreview.js` | Pending image thumbnail + remove |
| `frontend/src/lib/api.js` | `sendMessage()` helper wrapping fetch + FormData |

---

## Chunk 1: Project Scaffold + Layout

### Task 1: Initialize Next.js project

**Files:**
- Create: `frontend/package.json`, `frontend/next.config.js`, `frontend/tailwind.config.js`, `frontend/postcss.config.js`

- [ ] **Step 1: Create Next.js app with Tailwind**

```bash
cd /Users/jamie/Documents/Python_Basic_Study/SG-INNOVATION/SG_INNOVATION
npx create-next-app@latest frontend --js --tailwind --eslint --app --src-dir --no-import-alias --use-npm
```

Accept all defaults. This creates the full scaffold.

- [ ] **Step 2: Configure Tailwind design tokens**

Edit `frontend/tailwind.config.js` — add Figma colors:

```js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        cream: "#FFF5EE",
        "bubble-ai": "#FFE5E0",
        "bubble-user": "#9ECCF0",
        "mic-blue": "#9ECCF0",
      },
      borderRadius: {
        bubble: "35px",
      },
    },
  },
  plugins: [],
};
```

- [ ] **Step 3: Verify dev server starts**

```bash
cd frontend && npm run dev
```

Expected: Server starts on http://localhost:3000

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Next.js frontend with Tailwind and Figma design tokens"
```

### Task 2: Global layout (mobile frame)

**Files:**
- Modify: `frontend/src/app/layout.js`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Write globals.css**

Replace contents of `frontend/src/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body {
  height: 100%;
  background: #f0f0f0;
}
```

- [ ] **Step 2: Write layout.js with mobile frame**

Replace `frontend/src/app/layout.js`:

```jsx
import "./globals.css";

export const metadata = {
  title: "Health Companion",
  description: "AI Health Companion Chatbot",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="flex justify-center items-center min-h-screen bg-gray-200">
        <div className="w-[393px] h-[852px] bg-cream relative overflow-hidden shadow-xl rounded-[40px] border-[8px] border-gray-800">
          {children}
        </div>
      </body>
    </html>
  );
}
```

- [ ] **Step 3: Write root page redirect**

Replace `frontend/src/app/page.js`:

```jsx
import { redirect } from "next/navigation";
export default function Home() {
  redirect("/chat");
}
```

- [ ] **Step 4: Verify — browser shows cream background in phone frame**

Open http://localhost:3000 — should see a centered phone-shaped frame with cream background.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/
git commit -m "feat: add mobile frame layout with cream background"
```

---

## Chunk 2: Static Components (TopBar + MessageBubble + MessageList)

### Task 3: TopBar component

**Files:**
- Create: `frontend/src/components/TopBar.js`

- [ ] **Step 1: Write TopBar**

```jsx
"use client";

import { useState } from "react";

const AGENT_ICONS = {
  companion: "💞",
  expert: "🩺",
  crisis: "🩺",
};

export default function TopBar({ agentType = "companion" }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const icon = AGENT_ICONS[agentType] || "💞";

  return (
    <div className="flex items-center justify-between px-5 pt-12 pb-3 bg-cream">
      <div className="flex items-center gap-2">
        <h1 className="text-2xl font-bold italic">Chat</h1>
        <span className="text-xl">{icon}</span>
      </div>

      <button onClick={() => setMenuOpen(!menuOpen)} className="text-2xl p-1">
        ☰
      </button>

      {menuOpen && (
        <div className="absolute right-4 top-24 bg-white rounded-xl shadow-lg z-50 py-2 min-w-[140px]">
          {["Home", "Chat", "Task"].map((item) => (
            <button
              key={item}
              className="block w-full text-left px-4 py-2 hover:bg-gray-100 text-sm"
              onClick={() => setMenuOpen(false)}
            >
              {item}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/TopBar.js
git commit -m "feat: add TopBar component with agent icon and hamburger menu"
```

### Task 4: MessageBubble component

**Files:**
- Create: `frontend/src/components/MessageBubble.js`

- [ ] **Step 1: Write MessageBubble**

```jsx
export default function MessageBubble({ role, content, image }) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3 px-4`}>
      <div
        className={`max-w-[70%] px-4 py-3 ${
          isUser
            ? "bg-bubble-user rounded-bubble rounded-br-lg"
            : "bg-bubble-ai rounded-bubble rounded-bl-lg"
        }`}
      >
        {image && (
          <img
            src={image}
            alt="uploaded"
            className="w-full rounded-2xl mb-2 max-h-48 object-cover"
          />
        )}
        {content && <p className="text-sm leading-relaxed">{content}</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/MessageBubble.js
git commit -m "feat: add MessageBubble with pink/blue Figma colors"
```

### Task 5: MessageList component

**Files:**
- Create: `frontend/src/components/MessageList.js`

- [ ] **Step 1: Write MessageList**

```jsx
"use client";

import { useEffect, useRef } from "react";
import MessageBubble from "./MessageBubble";

export default function MessageList({ messages, isLoading }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="flex-1 overflow-y-auto py-4">
      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          role={msg.role}
          content={msg.content}
          image={msg.image}
        />
      ))}

      {isLoading && (
        <div className="flex justify-start mb-3 px-4">
          <div className="bg-bubble-ai rounded-bubble rounded-bl-lg px-5 py-3">
            <div className="flex gap-1">
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.15s]" />
              <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:0.3s]" />
            </div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/MessageList.js
git commit -m "feat: add MessageList with auto-scroll and loading indicator"
```

---

## Chunk 3: Input Components (InputBar + ActionSheet + ImagePreview)

### Task 6: ImagePreview component

**Files:**
- Create: `frontend/src/components/ImagePreview.js`

- [ ] **Step 1: Write ImagePreview**

```jsx
export default function ImagePreview({ src, onRemove }) {
  if (!src) return null;

  return (
    <div className="px-4 pb-2 flex items-center gap-2">
      <div className="relative">
        <img
          src={src}
          alt="pending upload"
          className="w-16 h-16 object-cover rounded-xl border border-gray-200"
        />
        <button
          onClick={onRemove}
          className="absolute -top-2 -right-2 w-5 h-5 bg-red-400 text-white rounded-full text-xs flex items-center justify-center"
        >
          ×
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ImagePreview.js
git commit -m "feat: add ImagePreview thumbnail with remove button"
```

### Task 7: ActionSheet component

**Files:**
- Create: `frontend/src/components/ActionSheet.js`

- [ ] **Step 1: Write ActionSheet**

```jsx
export default function ActionSheet({ visible, onCamera, onGallery, onClose }) {
  if (!visible) return null;

  return (
    <div className="absolute inset-0 z-40 flex items-end">
      <div className="absolute inset-0 bg-black/30" onClick={onClose} />

      <div className="relative w-full bg-white rounded-t-2xl z-50 pb-6">
        <div className="text-center py-3 border-b">
          <p className="font-semibold text-sm">Upload</p>
        </div>

        <button
          onClick={onCamera}
          className="w-full py-3 text-center text-sm hover:bg-gray-50 border-b"
        >
          Open Camera
        </button>
        <button
          onClick={onGallery}
          className="w-full py-3 text-center text-sm hover:bg-gray-50 border-b"
        >
          Open Gallery
        </button>
        <button
          onClick={onClose}
          className="w-full py-3 text-center text-sm text-red-500 hover:bg-gray-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/ActionSheet.js
git commit -m "feat: add ActionSheet bottom sheet for camera/gallery"
```

### Task 8: InputBar component

**Files:**
- Create: `frontend/src/components/InputBar.js`

- [ ] **Step 1: Write InputBar**

```jsx
"use client";

import { useState, useRef } from "react";

export default function InputBar({
  onSendText,
  onSendAudio,
  onOpenSheet,
  disabled,
}) {
  const [text, setText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const inputRef = useRef(null);

  const handleSendText = () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSendText(trimmed);
    setText("");
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendText();
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        if (blob.size > 0) onSendAudio(blob);
      };

      mediaRecorderRef.current = recorder;
      recorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error("Mic access denied:", err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
  };

  return (
    <div className="px-4 pb-6 pt-2 bg-cream">
      {/* Text input row — visible when user taps Aa */}
      {text !== "" && (
        <div className="flex items-center gap-2 mb-3">
          <input
            ref={inputRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type a message..."
            className="flex-1 bg-white rounded-full px-4 py-2 text-sm outline-none border border-gray-200"
            disabled={disabled}
          />
          <button
            onClick={handleSendText}
            className="bg-bubble-user text-white rounded-full w-9 h-9 flex items-center justify-center text-lg"
            disabled={disabled}
          >
            ↑
          </button>
        </div>
      )}

      {/* Main button row */}
      <div className="flex items-center justify-between">
        {/* Text button */}
        <button
          onClick={() => {
            setText(" ");
            setTimeout(() => {
              setText("");
              inputRef.current?.focus();
            }, 0);
          }}
          className="w-[51px] h-[54px] flex items-center justify-center text-gray-500"
        >
          <span className="text-xl font-serif italic">Aa</span>
        </button>

        {/* Mic button */}
        <button
          onMouseDown={startRecording}
          onMouseUp={stopRecording}
          onTouchStart={startRecording}
          onTouchEnd={stopRecording}
          className={`w-[110px] h-[110px] rounded-full flex items-center justify-center transition-colors ${
            isRecording ? "bg-red-400 scale-110" : "bg-mic-blue"
          }`}
          disabled={disabled}
        >
          <span className="text-4xl">🎙</span>
        </button>

        {/* Add button */}
        <button
          onClick={onOpenSheet}
          className="w-[60px] h-[60px] rounded-full bg-gray-200 flex items-center justify-center text-2xl text-gray-600"
          disabled={disabled}
        >
          ＋
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/InputBar.js
git commit -m "feat: add InputBar with text, voice recording, and upload button"
```

---

## Chunk 4: API Layer + Chat Page Integration

### Task 9: API helper

**Files:**
- Create: `frontend/src/lib/api.js`

- [ ] **Step 1: Write sendMessage helper**

```js
const API_URL = "http://localhost:8000/chat/message";

export async function sendMessage({ userId, sessionId, text, image, audio }) {
  const form = new FormData();
  form.append("user_id", userId);

  if (sessionId) form.append("session_id", sessionId);
  if (text) form.append("text", text);
  if (image) form.append("image", image);
  if (audio) form.append("audio", audio, "recording.webm");

  const res = await fetch(API_URL, { method: "POST", body: form });

  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
  }

  return res.json();
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/api.js
git commit -m "feat: add API helper for chat message endpoint"
```

### Task 10: Chat page — wire everything together

**Files:**
- Create: `frontend/src/app/chat/page.js`

- [ ] **Step 1: Write chat page**

```jsx
"use client";

import { useState, useRef } from "react";
import TopBar from "../../components/TopBar";
import MessageList from "../../components/MessageList";
import InputBar from "../../components/InputBar";
import ActionSheet from "../../components/ActionSheet";
import ImagePreview from "../../components/ImagePreview";
import { sendMessage } from "../../lib/api";

const USER_ID = "demo_user";

export default function ChatPage() {
  const [messages, setMessages] = useState([]);
  const [sessionId, setSessionId] = useState(null);
  const [agentType, setAgentType] = useState("companion");
  const [isLoading, setIsLoading] = useState(false);
  const [pendingImage, setPendingImage] = useState(null);
  const [pendingImageFile, setPendingImageFile] = useState(null);
  const [sheetOpen, setSheetOpen] = useState(false);

  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const msgIdRef = useRef(0);

  const nextId = () => {
    msgIdRef.current += 1;
    return msgIdRef.current;
  };

  const addMessage = (role, content, image = null) => {
    const msg = { id: nextId(), role, content, image };
    setMessages((prev) => [...prev, msg]);
    return msg;
  };

  const handleSend = async ({ text, audio, image, imagePreview }) => {
    // Add user message to chat
    addMessage("user", text || (audio ? "🎙 Voice message" : ""), imagePreview || null);

    // Clear pending image
    setPendingImage(null);
    setPendingImageFile(null);

    setIsLoading(true);
    try {
      const data = await sendMessage({
        userId: USER_ID,
        sessionId,
        text: text || undefined,
        image: image || undefined,
        audio: audio || undefined,
      });

      if (!sessionId) setSessionId(data.session_id);
      setAgentType(data.agent_type);
      addMessage("assistant", data.reply);
    } catch (err) {
      console.error("Send failed:", err);
      addMessage("assistant", "Sorry, something went wrong. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const handleSendText = (text) => {
    handleSend({
      text,
      image: pendingImageFile,
      imagePreview: pendingImage,
    });
  };

  const handleSendAudio = (audioBlob) => {
    handleSend({
      audio: audioBlob,
      image: pendingImageFile,
      imagePreview: pendingImage,
    });
  };

  const handleImageSelected = (file) => {
    setPendingImageFile(file);
    setPendingImage(URL.createObjectURL(file));
    setSheetOpen(false);
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) handleImageSelected(file);
    e.target.value = "";
  };

  return (
    <div className="flex flex-col h-full bg-cream">
      <TopBar agentType={agentType} />

      <MessageList messages={messages} isLoading={isLoading} />

      <ImagePreview
        src={pendingImage}
        onRemove={() => {
          setPendingImage(null);
          setPendingImageFile(null);
        }}
      />

      <InputBar
        onSendText={handleSendText}
        onSendAudio={handleSendAudio}
        onOpenSheet={() => setSheetOpen(true)}
        disabled={isLoading}
      />

      <ActionSheet
        visible={sheetOpen}
        onCamera={() => cameraInputRef.current?.click()}
        onGallery={() => fileInputRef.current?.click()}
        onClose={() => setSheetOpen(false)}
      />

      {/* Hidden file inputs */}
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={handleFileChange}
      />
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="hidden"
        onChange={handleFileChange}
      />
    </div>
  );
}
```

- [ ] **Step 2: Delete default Next.js page content**

Remove the default content from `frontend/src/app/page.js` (already handled in Task 2).

- [ ] **Step 3: Verify full flow**

1. Start backend: `cd /Users/jamie/Documents/Python_Basic_Study/SG-INNOVATION/SG_INNOVATION && uvicorn chatbot.api.main:api --reload --port 8000`
2. Start frontend: `cd frontend && npm run dev`
3. Open http://localhost:3000
4. Should see phone frame → Chat page with TopBar and InputBar
5. Type a message → should see pink AI reply bubble
6. Agent icon should update based on response

- [ ] **Step 4: Commit**

```bash
git add frontend/src/
git commit -m "feat: wire Chat page with API integration and all components"
```

---

## Chunk 5: Polish + Final Verification

### Task 11: Visual polish pass

**Files:**
- Modify: `frontend/src/components/InputBar.js`
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Add Figma-matching polish**

Adjustments to make after visual comparison with Figma screenshot:
- Ensure bubble colors exactly match `#FFE5E0` and `#9ECCF0`
- Verify border-radius matches 35px
- Tune InputBar spacing to match Figma (Aa left, mic center, + right)
- Add smooth transitions for ActionSheet open/close
- Ensure cream background `#FFF5EE` is consistent

- [ ] **Step 2: Test all three input modes**

1. Text: type message, hit Enter → verify user bubble + AI reply
2. Voice: hold mic, release → verify audio sent (may fail without MERaLiON, that's ok)
3. Image: tap +, select file → verify thumbnail shows, send with text → verify AI reply

- [ ] **Step 3: Test error handling**

1. Stop backend server
2. Send a message → should see error bubble
3. Restart backend → next message should work

- [ ] **Step 4: Final commit**

```bash
git add -A frontend/
git commit -m "feat: polish chat UI to match Figma design"
```
