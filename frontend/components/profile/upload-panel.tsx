"use client";

import { useRef, useState } from "react";
import { FileUp, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";

interface UploadPanelProps {
  onUploadPdf: (file: File) => Promise<void>;
  onSubmitText: (text: string) => Promise<void>;
  busy: boolean;
}

export function UploadPanel({
  onUploadPdf,
  onSubmitText,
  busy,
}: UploadPanelProps) {
  const [dragOver, setDragOver] = useState(false);
  const [pastedText, setPastedText] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  function handleFiles(files: FileList | null) {
    const file = files?.[0];
    if (file) void onUploadPdf(file);
  }

  return (
    <div className="grid gap-4 md:grid-cols-2">
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload CV PDF"
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => e.key === "Enter" && inputRef.current?.click()}
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
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
          dragOver ? "border-primary bg-accent" : "border-input"
        )}
      >
        {busy ? (
          <Loader2 className="h-6 w-6 animate-spin" aria-hidden />
        ) : (
          <FileUp className="h-6 w-6 text-muted-foreground" aria-hidden />
        )}
        <p className="text-sm font-medium">
          {busy ? "Extracting your profile…" : "Drop your CV PDF here"}
        </p>
        <p className="text-xs text-muted-foreground">
          or click to choose a file
        </p>
        <input
          ref={inputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
      </div>

      <div className="flex flex-col gap-2">
        <Textarea
          placeholder="Or paste free text — e.g. your LinkedIn About section…"
          value={pastedText}
          onChange={(e) => setPastedText(e.target.value)}
          className="flex-1"
        />
        <Button
          variant="secondary"
          disabled={busy || pastedText.trim().length < 50}
          onClick={() => void onSubmitText(pastedText)}
        >
          Extract from text
        </Button>
      </div>
    </div>
  );
}
