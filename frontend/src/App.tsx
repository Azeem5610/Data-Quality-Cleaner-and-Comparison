import { useCallback, useEffect, useState } from "react";
import { askQuestion, getHealth, getSamples, loadSample, processFile, processUrl } from "./api/client";
import { AnswerCompare } from "./components/AnswerCompare";
import { AskPanel } from "./components/AskPanel";
import { DiffView } from "./components/DiffView";
import { Icon } from "./components/Icon";
import { JunkScoreCard } from "./components/JunkScoreCard";
import { SourceInput } from "./components/SourceInput";
import type { AskResponse, ProcessResponse, SampleSource } from "./types";

type HealthStatus = "checking" | "connected" | "offline";

export default function App() {
  const [healthStatus, setHealthStatus] = useState<HealthStatus>("checking");
  const [samples, setSamples] = useState<SampleSource[]>([]);
  const [samplesLoading, setSamplesLoading] = useState(true);
  const [samplesError, setSamplesError] = useState(false);
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [answers, setAnswers] = useState<AskResponse | null>(null);
  const [question, setQuestion] = useState("");
  const [processing, setProcessing] = useState(false);
  const [loadingSample, setLoadingSample] = useState(false);
  const [asking, setAsking] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    let mounted = true;
    getHealth()
      .then((data) => { if (mounted) setHealthStatus(data.status === "ok" ? "connected" : "offline"); })
      .catch(() => { if (mounted) setHealthStatus("offline"); });
    getSamples()
      .then((data) => { if (mounted) setSamples(data); })
      .catch(() => { if (mounted) setSamplesError(true); })
      .finally(() => { if (mounted) setSamplesLoading(false); });
    return () => { mounted = false; };
  }, []);

  const startProcessing = useCallback(() => {
    setError("");
    setResult(null);
    setAnswers(null);
    setQuestion("");
  }, []);

  async function analyzeFile(file: File) {
    startProcessing();
    setProcessing(true);
    try {
      setResult(await processFile(file));
      setHealthStatus("connected");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not analyze this PDF.");
    } finally {
      setProcessing(false);
    }
  }

  async function analyzeUrl(url: string) {
    startProcessing();
    setProcessing(true);
    try {
      setResult(await processUrl(url));
      setHealthStatus("connected");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not analyze this URL.");
    } finally {
      setProcessing(false);
    }
  }

  async function analyzeSample(name: string) {
    startProcessing();
    setLoadingSample(true);
    try {
      setResult(await loadSample(name));
      setHealthStatus("connected");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load this sample.");
    } finally {
      setLoadingSample(false);
    }
  }

  async function ask(questionText: string) {
    if (!result) return;
    setError("");
    setAnswers(null);
    setQuestion(questionText);
    setAsking(true);
    try {
      setAnswers(await askQuestion({ source_id: result.source_id, question: questionText }));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not compare answers.");
    } finally {
      setAsking(false);
    }
  }

  async function copySourceId() {
    if (!result || !navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(result.source_id);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  }

  const busy = processing || loadingSample;
  const statusLabel = healthStatus === "connected" ? "Backend ready" : healthStatus === "checking" ? "Connecting" : "Backend unavailable";

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="topbar-inner">
          <a className="brand" href="#top" aria-label="Data Quality Cleaner and Comparison home">
            <span className="brand-mark"><Icon name="file" size={16} /></span>
            <span className="brand-title">Data Quality Cleaner <span>/</span> <b>Comparison</b></span>
          </a>
          <div className={`backend-status status-${healthStatus}`} role="status">
            <span className="status-dot" />{statusLabel}
          </div>
        </div>
      </header>

      <main className="workspace" id="top">
        <section className="page-intro">
          <div>
            <div className="eyebrow">Source analysis</div>
            <h1>Separate signal from source noise.</h1>
            <p>Inspect what is removed before comparing how source quality changes retrieval answers.</p>
          </div>
          {result && (
            <div className="source-id-chip">
              <span className="source-id-label">Source ID</span>
              <code>{result.source_id}</code>
              <button type="button" onClick={copySourceId} aria-label={copied ? "Source ID copied" : "Copy source ID"} title={copied ? "Copied" : "Copy source ID"}>
                {copied ? <Icon name="check" size={15} /> : <Icon name="copy" size={15} />}
              </button>
            </div>
          )}
        </section>

        <SourceInput
          samples={samples}
          samplesLoading={samplesLoading}
          samplesError={samplesError}
          busy={busy}
          onProcessFile={analyzeFile}
          onProcessUrl={analyzeUrl}
          onLoadSample={analyzeSample}
        />

        {error && (
          <div className="notice notice-error" role="alert">
            <Icon name="alert" size={18} />
            <span>{error}</span>
            <button type="button" className="notice-dismiss" onClick={() => setError("")} aria-label="Dismiss error">×</button>
          </div>
        )}

        {busy && (
          <div className="processing-notice" role="status">
            <Icon name="loader" size={17} className="spin" />
            <div><strong>{loadingSample ? "Preparing demo source" : "Analyzing source"}</strong><span>Extracting text, cleaning it, and building the comparison.</span></div>
          </div>
        )}

        {result ? (
          <div className="results-stack">
            <div className="result-source-line">
              <div className="result-file-icon"><Icon name={result.source_type === "pdf" ? "file" : "globe"} size={17} /></div>
              <div className="result-source-name"><span className="eyebrow">Current source</span><strong title={result.source_name}>{result.source_name}</strong></div>
              <span className="source-type-badge">{result.source_type === "pdf" ? "PDF document" : "Web page"}</span>
            </div>
            <JunkScoreCard result={result} />
            <DiffView result={result} />
            <section className="panel answer-panel" aria-labelledby="answers-title">
              <AskPanel disabled={!result} loading={asking} onAsk={ask} />
              <AnswerCompare response={answers} question={question} loading={asking} />
            </section>
          </div>
        ) : !busy ? (
          <section className="empty-workspace" aria-label="Analysis preview">
            <div className="empty-illustration" aria-hidden="true"><span><Icon name="file" size={22} /></span><span className="empty-check"><Icon name="check" size={13} /></span></div>
            <h2>Your comparison will appear here</h2>
            <p>Choose a PDF, enter a web address, or load a demo source to see the cleanup report and answer comparison.</p>
            <div className="empty-steps"><span><b>01</b> Add a source</span><i /><span><b>02</b> Review removed text</span><i /><span><b>03</b> Compare answers</span></div>
          </section>
        ) : null}

        <footer className="page-footer">
          <span>Data quality, made visible.</span>
          {healthStatus === "connected" && <span className="footer-health"><span className="status-dot" />Connected to local API</span>}
        </footer>
      </main>
    </div>
  );
}
