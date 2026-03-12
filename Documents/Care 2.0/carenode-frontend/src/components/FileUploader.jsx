export default function FileUploader({ onFileSelect }) {
  const handlePick = (event) => {
    const file = event.target.files?.[0];
    if (file) onFileSelect(file);
  };

  return (
    <div className="rounded border p-3">
      <label className="block text-sm font-medium text-slate-600">Lab report</label>
      <input
        className="mt-2 w-full rounded border px-2 py-2"
        type="file"
        accept="image/*,application/pdf"
        onChange={handlePick}
      />
      <p className="mt-1 text-xs text-slate-500">Upload image/pdf lab report for OCR analysis.</p>
    </div>
  );
}
