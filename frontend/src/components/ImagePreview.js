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
