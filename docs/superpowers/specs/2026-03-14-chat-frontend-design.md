# Chat Frontend Design Spec

> Date: 2026-03-14 | Figma: https://www.figma.com/design/3VKCArQBPF2qILnu8qliMO/Untitled?node-id=0-1

## Goal

Build the Chat page frontend in React (Next.js), faithfully reproducing the Figma design. Connects to existing FastAPI backend `POST /chat/message`. Only the Chat page for now; project structure supports adding Home/Task/Garden/Setting pages later.

## Tech Stack

- **Next.js 14** (App Router)
- **Tailwind CSS**
- **React useState** for state management
- **MediaRecorder API** for voice recording
- **fetch** for API calls (FormData for multipart uploads)

## Design Tokens (from Figma)

| Token | Value |
|-------|-------|
| Background | `#FFF5EE` cream/beige |
| AI bubble | `#FFE5E0` pink, border-radius 35px, left-aligned |
| User bubble | `#9ECCF0` blue, border-radius 36px, right-aligned |
| Mic button circle | `#9ECCF0` blue, 110x110px |
| Add button | 60x60px circle |
| Text input icon | 51x54px |
| Viewport | 393px (iPhone 16 width), mobile-first |

## Project Structure

```
frontend/
├── package.json
├── next.config.js
├── tailwind.config.js
├── src/
│   ├── app/
│   │   ├── layout.js           # Global layout, 393px mobile frame
│   │   ├── globals.css         # Tailwind + custom color vars
│   │   ├── page.js             # Redirect to /chat
│   │   └── chat/
│   │       └── page.js         # Chat page (main work)
│   └── components/
│       ├── TopBar.js           # "Chat" title + agent icon + hamburger
│       ├── MessageList.js      # Scrollable message area
│       ├── MessageBubble.js    # Single message bubble (text/image)
│       ├── InputBar.js         # Text + Mic + Upload button
│       ├── ActionSheet.js      # Upload bottom sheet
│       └── ImagePreview.js     # Pending image thumbnail
```

## Components

### TopBar
- Left: "Chat" title (decorative font) + agent type icon
  - `💞` companion (default), `🩺` expert
  - Auto-switches based on latest API response `agent_type`
- Right: `☰` hamburger icon (no text label)
  - On tap: shows navigation menu (Home / Chat / Task)
- Props: `agentType: "companion" | "expert" | "crisis"`
  - `"crisis"` displays as `🩺` (same as expert — crisis is a medical emergency)

### MessageList
- Scrollable container, full height between TopBar and InputBar
- Auto-scrolls to bottom on new messages
- Shows loading indicator ("..." animated bubble) while waiting for AI reply
- State: `messages: Array<{id, role, content, image?}>`

### MessageBubble
- AI messages: pink `#FFE5E0`, left-aligned, max-width ~70%
- User messages: blue `#9ECCF0`, right-aligned, max-width ~70%
- Image messages: show thumbnail (rounded corners), text below if present
- Border-radius: 35-36px

### InputBar
- Three elements in a row:
  - Left: `Aa` text icon — tap to focus text input (hidden input field, always available)
  - Center: Microphone button (large blue circle 110px) — press-and-hold to record, release to send
  - Right: `＋` add button (60px) — tap opens ActionSheet
- When text is typed, show a send button
- When image is pending, InputBar shows ImagePreview above it

### ActionSheet
- Bottom sheet overlay with backdrop
- Options: "Upload" title, "Open Camera", "Open Gallery", "Cancel"
- Open Camera: triggers `<input capture="environment">` (mobile camera)
- Open Gallery: triggers `<input type="file" accept="image/*">`
- Cancel: closes sheet

### ImagePreview
- Shows selected image as thumbnail above InputBar
- Has a `×` button to remove
- User can still type text or record voice with image attached

## Data Flow

```
User action (type/record/photo)
  → InputBar collects {text?, audio?, image?}
  → POST /chat/message as FormData
     {user_id, session_id?, text?, image?, audio?}
  → Response: {session_id, reply, agent_type}
  → Update: messages[], sessionId, agentType state
  → MessageList re-renders, scrolls to bottom
  → TopBar updates agent icon
```

## State (Chat page)

```js
const [messages, setMessages] = useState([])
const [sessionId, setSessionId] = useState(null)
const [agentType, setAgentType] = useState("companion")
const [isLoading, setIsLoading] = useState(false)
const [pendingImage, setPendingImage] = useState(null)
```

## Session Behavior

- No chat history / past conversations
- `sessionId` starts as `null`, set from first API response
- On every message after the first, `session_id` from previous response must be included
- Navigating away from Chat = session lost (state reset)

## Error Handling

- API 500 / network timeout: show error message bubble in chat ("Sorry, something went wrong. Please try again.")
- Empty audio blob: ignore, don't send
- Image upload fails: show brief toast/error, don't send

## Voice Recording

- `MediaRecorder` API with `audio/webm` format
- `onTouchStart` / `onMouseDown`: start recording
- `onTouchEnd` / `onMouseUp`: stop recording, send audio blob
- Visual feedback: mic button changes color/animation while recording

## API Integration

- Backend: `http://localhost:8000/chat/message`
- Request: `multipart/form-data` via `fetch` + `FormData`
- `user_id`: hardcoded for now (e.g., `"demo_user"`)
- CORS: configured in `main.py` (allows `localhost:3000`)

## Not In Scope

- Alert popups (Alert Agent, Julia's module)
- Task / Home / Garden / Setting page implementations
- User authentication / login
- Chat history persistence across sessions
