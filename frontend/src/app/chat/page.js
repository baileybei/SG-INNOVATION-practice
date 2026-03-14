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
    const userMsgId = nextId();
    const userMsg = {
      id: userMsgId,
      role: "user",
      content: text || (audio ? "🎙 Recording..." : ""),
      image: imagePreview || null,
    };
    setMessages((prev) => [...prev, userMsg]);

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

      // Update voice message bubble with transcribed text
      if (audio && data.transcribed_text) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === userMsgId
              ? { ...m, content: `🎙 ${data.transcribed_text}` }
              : m
          )
        );
      }

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
