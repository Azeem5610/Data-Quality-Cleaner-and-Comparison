import { useRef, useState, type DragEvent, type FormEvent } from "react";
import type { SampleSource } from "../types";
import { Icon } from "./Icon";

type SourceMode = "pdf" | "url";

interface SourceInputProps {
  samples: SampleSource[];
  samplesLoading: boolean;
  samplesError: boolean;
  busy: boolean;
  onProcessFile: (file: File) => void;
  onProcessUrl: (url: string) => void;
  onLoadSample: (name: string) => void;
}

const MAX_FILE_SIZE = 25 * 1024 * 1024;

export function SourceInput({
  samples,
  samplesLoading,
  samplesError,
  busy,
  onProcessFile,
  onProcessUrl,
  onLoadSample,
}: SourceInputProps) {
  const [mode, setMode] = useState<SourceMode>("pdf");
  const [file, setFile] = useState<File | null>(null);
  const [url, setUrl] = useState("");
  const [sampleName, setSampleName] = useState("");
  const [dragging, setDragging] = useState(false);
  const [inputError, setInputError] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);

  function chooseFile(candidate?: File) {
    if (!candidate) return;
    if (!candidate.name.toLowerCase().endsWith(".pdf") && candidate.type !== "application/pdf") {
      setInputError("Choose a PDF file to continue.");
      setFile(null);
      return;
    }
    if (candidate.size > MAX_FILE_SIZE) {
      setInputError("This PDF is larger than 25 MB.");
      setFile(null);
      return;
    }
    setInputError("");
    setFile(candidate);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setDragging(false);
    chooseFile(event.dataTransfer.files[0]);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setInputError("");
    if (mode === "pdf") {
      if (!file) {
        setInputError("Choose a PDF file first.");
        return;
      }
      onProcessFile(file);
      return;
    }

    const candidate = url.trim();
    try {
      const parsed = new URL(candidate.includes("://") ? candidate : `https://${candidate}`);
      if (!parsed.hostname.includes(".") || !["http:", "https:"].includes(parsed.protocol)) {
        throw new Error("Invalid URL");
      }
    } catch {
      setInputError("Enter a valid website URL, such as https://example.com/article.");
      return;
    }
    onProcessUrl(candidate);
  }

  return (
    <section className="panel source-panel" aria-labelledby="source-title">
      <div className="panel-heading source-heading">
        <div>
          <div className="eyebrow">Start here</div>
          <h2 id="source-title">Add a source</h2>
          <p>Upload a document or inspect a public web page.</p>
        </div>
        <div className="segmented-control" role="tablist" aria-label="Source type">
          <button
            type="button"
            role="tab"
            aria-selected={mode === "pdf"}
            className={mode === "pdf" ? "segment active" : "segment"}
            onClick={() => { setMode("pdf"); setInputError(""); }}
          >
            <Icon name="file" size={15} /> PDF file
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === "url"}
            className={mode === "url" ? "segment active" : "segment"}
            onClick={() => { setMode("url"); setInputError(""); }}
          >
            <Icon name="globe" size={15} /> Web URL
          </button>
        </div>
      </div>

      <form onSubmit={submit}>
        <div className="source-form-row">
          {mode === "pdf" ? (
            <div className="dropzone-wrap">
              <label
                className={`dropzone${dragging ? " is-dragging" : ""}${file ? " has-file" : ""}`}
                htmlFor="source-file"
                onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                onDragLeave={() => setDragging(false)}
                onDrop={handleDrop}
              >
                <input
                  ref={fileInput}
                  id="source-file"
                  type="file"
                  accept=".pdf,application/pdf"
                  className="visually-hidden"
                  onChange={(event) => chooseFile(event.currentTarget.files?.[0])}
                  disabled={busy}
                />
                <span className="dropzone-icon"><Icon name={file ? "check" : "upload"} size={18} /></span>
                <span className="dropzone-title">
                  {file ? file.name : <>Drop a PDF here, or <span className="text-link">browse files</span></>}
                </span>
                <span className="dropzone-help">PDF up to 25 MB · text will be extracted for review</span>
              </label>
              {file && <button className="clear-file" type="button" onClick={() => { setFile(null); if (fileInput.current) fileInput.current.value = ""; }}>Remove file</button>}
            </div>
          ) : (
            <div className="url-field-wrap">
              <label htmlFor="source-url" className="field-label">Page URL</label>
              <div className="url-field">
                <Icon name="link" size={17} />
                <input
                  id="source-url"
                  type="text"
                  inputMode="url"
                  value={url}
                  onChange={(event) => setUrl(event.target.value)}
                  placeholder="https://example.com/report"
                  disabled={busy}
                />
              </div>
              <p className="field-note">We’ll extract the visible page text, including navigation and footers.</p>
            </div>
          )}

          <div className="source-actions">
            <button className="button button-primary analyze-button" type="submit" disabled={busy}>
              {busy ? <><Icon name="loader" size={16} className="spin" /> Analyzing</> : <><Icon name="sparkle" size={16} /> Analyze source</>}
            </button>
            <div className="sample-control">
              <label htmlFor="sample-source">Or try a demo</label>
              <div className="sample-select-row">
                <select
                  id="sample-source"
                  value={sampleName}
                  onChange={(event) => setSampleName(event.target.value)}
                  disabled={busy || samplesLoading || samples.length === 0}
                >
                  <option value="">{samplesLoading ? "Loading samples…" : samplesError ? "Samples unavailable" : "Choose a sample"}</option>
                  {samples.map((sample) => <option value={sample.name} key={sample.name}>{sample.label}</option>)}
                </select>
                <button
                  type="button"
                  className="button button-secondary load-sample"
                  disabled={busy || !sampleName}
                  onClick={() => onLoadSample(sampleName)}
                  aria-label="Load selected sample"
                >
                  Load
                </button>
              </div>
            </div>
          </div>
        </div>
        {inputError && <p className="field-error" role="alert">{inputError}</p>}
        <p className="privacy-note"><span className="status-dot" />Source text is processed for this comparison and stored locally for retrieval.</p>
      </form>
    </section>
  );
}
