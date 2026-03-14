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
    <div className="flex items-center justify-between px-5 pt-14 pb-3 bg-cream">
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
