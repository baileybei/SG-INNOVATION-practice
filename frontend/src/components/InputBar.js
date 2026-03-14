"use client";

import { useState, useRef } from "react";
import { webmToWav } from "../lib/audioUtils";

export default function InputBar({
  onSendText,
  onSendAudio,
  onOpenSheet,
  disabled,
}) {
  const [text, setText] = useState("");
  const [showInput, setShowInput] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const inputRef = useRef(null);

  const handleSendText = () => {
    const trimmed = text.trim();
    if (!trimmed) return;
    onSendText(trimmed);
    setText("");
    setShowInput(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendText();
    }
  };

  const streamRef = useRef(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      const recorder = new MediaRecorder(stream, { mimeType: "audio/webm" });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = async () => {
        const webmBlob = new Blob(chunksRef.current, { type: "audio/webm" });
        stream.getTracks().forEach((t) => t.stop());
        if (webmBlob.size > 1000) {
          try {
            const wavBlob = await webmToWav(webmBlob);
            onSendAudio(wavBlob);
          } catch (err) {
            console.error("WAV conversion failed, sending WebM:", err);
            onSendAudio(webmBlob);
          }
        }
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

  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className="px-4 pb-6 pt-2 bg-cream">
      {/* Text input row */}
      {showInput && (
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
            setShowInput(true);
            setTimeout(() => inputRef.current?.focus(), 50);
          }}
          className="w-[51px] h-[54px] flex items-center justify-center text-gray-500"
        >
          <span className="text-xl font-serif italic">Aa</span>
        </button>

        {/* Mic button — tap to start, tap again to stop */}
        <button
          onClick={toggleRecording}
          className={`w-[110px] h-[110px] rounded-full flex flex-col items-center justify-center transition-all ${
            isRecording ? "bg-red-400 scale-110" : "bg-mic-blue"
          }`}
          disabled={disabled}
        >
          <span className="text-4xl">🎙</span>
          {isRecording && (
            <span className="text-xs text-white mt-1">Recording...</span>
          )}
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
