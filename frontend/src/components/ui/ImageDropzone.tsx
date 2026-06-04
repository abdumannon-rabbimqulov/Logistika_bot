import React, { useCallback, useState } from "react";
import { ImagePlus, Loader2 } from "lucide-react";
import { resolveMediaUrl } from "../../api";

interface ImageDropzoneProps {
  imageUrl: string | null;
  onUpload: (file: File) => Promise<void>;
  onUrlChange: (url: string | null) => void;
  uploading?: boolean;
}

export const ImageDropzone: React.FC<ImageDropzoneProps> = ({
  imageUrl,
  onUpload,
  onUrlChange,
  uploading,
}) => {
  const [dragOver, setDragOver] = useState(false);

  const handleFiles = useCallback(
    async (files: FileList | null) => {
      const file = files?.[0];
      if (!file?.type.startsWith("image/")) return;
      await onUpload(file);
    },
    [onUpload]
  );

  const preview = resolveMediaUrl(imageUrl);

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={`relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 transition ${
          dragOver
            ? "border-cyan-400 bg-cyan-500/10"
            : "border-slate-600 bg-slate-800/40 hover:border-slate-500"
        }`}
      >
        {uploading ? (
          <Loader2 className="animate-spin text-cyan-400" size={32} />
        ) : (
          <>
            <ImagePlus className="text-slate-400 mb-2" size={32} />
            <p className="text-sm text-slate-300 text-center">Rasmni sudrab tashlang yoki bosing</p>
          </>
        )}
        <input
          type="file"
          accept="image/*"
          className="absolute inset-0 opacity-0 cursor-pointer"
          disabled={uploading}
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>
      {preview && (
        <img src={preview} alt="" className="h-28 w-full object-contain rounded-lg bg-slate-800" />
      )}
      <div>
        <label className="text-xs font-medium text-slate-400">image_url (matn)</label>
        <input
          type="text"
          className="mt-1 w-full rounded-lg border border-slate-600 bg-slate-800 px-3 py-2.5 text-sm text-white min-h-[44px]"
          placeholder="/static/uploads/..."
          value={imageUrl ?? ""}
          onChange={(e) => onUrlChange(e.target.value || null)}
        />
      </div>
    </div>
  );
};
