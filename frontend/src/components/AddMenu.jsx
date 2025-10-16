import React, { useRef, useState } from "react";

export default function AddMenu({ onSolveResponse, onUserImageMessage }) {
  const [open, setOpen] = useState(false);
  const fileRef = useRef(null);
  const [loading, setLoading] = useState(false);

  // Set this in frontend/.env:  VITE_API_URL=https://<api-id>.execute-api.<region>.amazonaws.com/prod
  const base = import.meta?.env?.VITE_API_URL || "https://YOUR_API_GATEWAY_URL";
  const API_URL = `${base.replace(/\/+$/,"")}/solve`;

  async function fileToBase64(file) {
    const arrayBuffer = await file.arrayBuffer();
    const bytes = new Uint8Array(arrayBuffer);
    let binary = "";
    for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
    return btoa(binary);
  }

  function handlePickFile() {
    fileRef.current?.click();
  }

  async function handleFileChange(e) {
    const f = e.target.files && e.target.files[0];
    if (!f) return;

    // Textract supports ONLY PNG, JPG/JPEG, PDF
    const okTypes = ["image/png", "image/jpeg", "application/pdf"];
    if (!okTypes.includes(f.type)) {
      alert("Please upload a PNG, JPG, or PDF. (HEIC/WEBP are not supported.)");
      if (fileRef.current) fileRef.current.value = "";
      return;
    }

    setOpen(false);
    setLoading(true);

    // show the user's image in chat immediately (skip for PDFs)
    if (f.type !== "application/pdf") {
      const imgURL = URL.createObjectURL(f);
      onUserImageMessage?.(imgURL);
    }

    try {
      const b64 = await fileToBase64(f);
      const r = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_base64: b64 }),
      });

      // try to parse JSON; if the backend sent text, this will throw
      const j = await r.json();
      if (!r.ok) {
        throw new Error(j?.error || `HTTP ${r.status}`);
      }

      onSolveResponse?.({
        ocr_text: j.ocr_text,
        parsed_expression: j.parsed_expression,
        result: j.result,
      });
    } catch (err) {
      onSolveResponse?.({
        ocr_text: "",
        parsed_expression: "",
        result: `Error: ${err.message || err}`,
      });
    } finally {
      setLoading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  }

  return (
    <>
      {/* Floating + button */}
      <div style={{ position: "fixed", right: 24, bottom: 24, zIndex: 50 }}>
        <button
          aria-label="Add"
          onClick={() => setOpen((v) => !v)}
          style={{
            width: 56,
            height: 56,
            borderRadius: "9999px",
            border: "1px solid rgba(255,255,255,0.1)",
            background: "linear-gradient(180deg,#253042,#101826)",
            color: "#e5e7eb",
            fontSize: 28,
            lineHeight: "28px",
            boxShadow: "0 10px 30px rgba(0,0,0,0.35)",
            cursor: "pointer",
          }}
          disabled={loading}
        >
          {loading ? "…" : "+"}
        </button>

        {open && (
          <div
            style={{
              position: "absolute",
              right: 0,
              bottom: 70,
              background: "rgba(16,24,38,0.98)",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: 12,
              padding: 10,
              width: 220,
              boxShadow: "0 12px 30px rgba(0,0,0,0.45)",
              backdropFilter: "blur(8px)",
            }}
          >
            <div style={{ fontSize: 12, color: "#9ca3af", marginBottom: 6 }}>
              Add to chat
            </div>

            <button
              onClick={handlePickFile}
              style={{
                width: "100%",
                textAlign: "left",
                padding: "10px 12px",
                borderRadius: 8,
                border: "1px solid rgba(255,255,255,0.06)",
                background: "transparent",
                color: "#e5e7eb",
                cursor: "pointer",
              }}
            >
              📎 Upload photo / file
            </button>
          </div>
        )}
      </div>

      <input
        ref={fileRef}
        type="file"
        accept=".png,.jpg,.jpeg,.pdf"
        hidden
        onChange={handleFileChange}
      />
    </>
  );
}

