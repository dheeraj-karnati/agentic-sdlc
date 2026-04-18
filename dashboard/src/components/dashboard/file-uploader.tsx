"use client";

import { useCallback, useState, useRef } from "react";
import { Upload, X, FileText, Code, Music, Video, Archive, Image, Link2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const FILE_TYPES = [
  { ext: "PDF", color: "text-blue-400" }, { ext: "DOCX", color: "text-blue-400" },
  { ext: "XLSX", color: "text-blue-400" }, { ext: "MD", color: "text-blue-400" },
  { ext: "PY", color: "text-green-400" }, { ext: "JS", color: "text-green-400" },
  { ext: "TS", color: "text-green-400" }, { ext: "SQL", color: "text-green-400" },
  { ext: "MP3", color: "text-amber-400" }, { ext: "MP4", color: "text-amber-400" },
  { ext: "PNG", color: "text-teal-400" }, { ext: "ZIP", color: "text-purple-400" },
];

function getFileIcon(name: string) {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (["py", "js", "ts", "tsx", "java", "go", "rs", "sql"].includes(ext)) return Code;
  if (["mp3", "wav", "m4a", "ogg"].includes(ext)) return Music;
  if (["mp4", "mov", "avi", "webm"].includes(ext)) return Video;
  if (["zip", "tar", "gz"].includes(ext)) return Archive;
  if (["png", "jpg", "jpeg", "gif", "svg"].includes(ext)) return Image;
  return FileText;
}

function getTypeBadge(name: string): { label: string; cls: string } {
  const ext = name.split(".").pop()?.toLowerCase() ?? "";
  if (["pdf", "docx", "xlsx", "txt", "md", "html"].includes(ext)) return { label: "Document", cls: "bg-blue-500/10 text-blue-400 border-blue-500/20" };
  if (["py", "js", "ts", "tsx", "java", "go", "rs", "sql", "json", "yaml"].includes(ext)) return { label: "Code", cls: "bg-green-500/10 text-green-400 border-green-500/20" };
  if (["mp3", "wav", "m4a", "mp4", "mov", "avi", "webm"].includes(ext)) return { label: "Media", cls: "bg-amber-500/10 text-amber-400 border-amber-500/20" };
  if (["zip", "tar", "gz"].includes(ext)) return { label: "Archive", cls: "bg-purple-500/10 text-purple-400 border-purple-500/20" };
  if (["png", "jpg", "jpeg", "gif", "svg"].includes(ext)) return { label: "Image", cls: "bg-teal-500/10 text-teal-400 border-teal-500/20" };
  return { label: "File", cls: "bg-gray-500/10 text-gray-400 border-gray-500/20" };
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

interface FileUploaderProps {
  files: File[];
  onFilesChange: (files: File[]) => void;
}

export function FileUploader({ files, onFilesChange }: FileUploaderProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const arr = Array.from(newFiles);
    onFilesChange([...files, ...arr]);
  }, [files, onFilesChange]);

  const removeFile = (index: number) => {
    onFilesChange(files.filter((_, i) => i !== index));
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files);
  }, [addFiles]);

  const totalSize = files.reduce((s, f) => s + f.size, 0);

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all",
          isDragging
            ? "border-d8x-blue bg-d8x-blue/5"
            : "border-d8x-border hover:border-d8x-border-hover",
        )}
      >
        <Upload className="w-8 h-8 mx-auto text-d8x-text-tertiary mb-3" />
        <p className="text-sm font-medium text-d8x-text-primary">Drop files to analyze</p>
        <p className="text-xs text-d8x-text-secondary mt-1">BRDs, source code, recordings, diagrams — any format</p>
        <div className="flex flex-wrap justify-center gap-1.5 mt-4">
          {FILE_TYPES.map((ft) => (
            <span key={ft.ext} className={cn("text-[10px] px-1.5 py-0.5 rounded border border-d8x-border", ft.color)}>{ft.ext}</span>
          ))}
        </div>
        <input ref={inputRef} type="file" multiple className="hidden" onChange={(e) => e.target.files && addFiles(e.target.files)} />
      </div>

      {/* URL import */}
      <div className="flex gap-2">
        <Input
          value={urlInput}
          onChange={(e) => setUrlInput(e.target.value)}
          placeholder="S3, GCS, SharePoint, or HTTP URL"
          className="bg-d8x-background border-d8x-border text-sm"
        />
        <Button
          variant="outline"
          size="sm"
          disabled={!urlInput.trim()}
          onClick={() => { /* URL import handled at parent level */ setUrlInput(""); }}
          className="border-d8x-border shrink-0"
        >
          <Link2 className="w-4 h-4 mr-1" />
          Import
        </Button>
      </div>

      {/* File list */}
      {files.length > 0 && (
        <div className="border border-d8x-border rounded-lg divide-y divide-d8x-border">
          {files.map((f, i) => {
            const Icon = getFileIcon(f.name);
            const badge = getTypeBadge(f.name);
            return (
              <div key={i} className="flex items-center gap-3 px-3 py-2 hover:bg-d8x-surface-hover transition-colors">
                <Icon className="w-4 h-4 text-d8x-text-secondary shrink-0" />
                <span className="text-sm truncate flex-1">{f.name}</span>
                <span className={cn("text-[10px] px-1.5 py-0.5 rounded border", badge.cls)}>{badge.label}</span>
                <span className="text-xs text-d8x-text-tertiary">{formatSize(f.size)}</span>
                <button onClick={() => removeFile(i)} className="text-d8x-text-tertiary hover:text-d8x-danger transition-colors">
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            );
          })}
          <div className="px-3 py-2 text-xs text-d8x-text-secondary">
            {files.length} file{files.length !== 1 ? "s" : ""}, {formatSize(totalSize)} total
          </div>
        </div>
      )}
    </div>
  );
}
