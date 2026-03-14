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
