export default function MessageBubble({ role, content, image }) {
  const isUser = role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3 px-4`}>
      <div
        className={`max-w-[70%] px-4 py-3 ${
          isUser
            ? "bg-bubble-user rounded-[36px] rounded-br-lg"
            : "bg-bubble-ai rounded-[35px] rounded-bl-lg"
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
