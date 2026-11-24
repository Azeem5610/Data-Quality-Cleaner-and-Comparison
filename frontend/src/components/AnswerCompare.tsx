import type { AskResponse, AskSideResponse } from "../types";
import { Icon } from "./Icon";

interface AnswerCompareProps {
  response: AskResponse | null;
  question: string;
  loading: boolean;
}

function AnswerCard({ title, side, accent }: { title: string; side: AskSideResponse; accent: "raw" | "clean" }) {
  return (
    <article className={`answer-card answer-${accent}`}>
      <header className="answer-card-heading">
        <span className="diff-label"><span className={`source-indicator ${accent}-indicator`} /> {title}</span>
        <span className="chunk-count">{side.chunks.length} {side.chunks.length === 1 ? "chunk" : "chunks"}</span>
      </header>
      <div className="answer-body">
        <p className="answer-copy">{side.answer}</p>
        {side.chunks.length > 0 && (
          <details className="chunk-details">
            <summary><Icon name="chevron" size={14} /> View retrieved chunks</summary>
            <div className="chunk-list">
              {side.chunks.map((chunk) => (
                <div className="retrieved-chunk" key={`${chunk.chunk_index}-${chunk.start}`}>
                  <div className="chunk-meta"><span>Chunk {chunk.chunk_index + 1}</span><span>{chunk.start.toLocaleString()}–{chunk.end.toLocaleString()}</span></div>
                  <p>{chunk.text}</p>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </article>
  );
}

export function AnswerCompare({ response, question, loading }: AnswerCompareProps) {
  if (!response && !loading) {
    return (
      <div className="answer-empty">
        <span className="empty-icon"><Icon name="sparkle" size={19} /></span>
        <span>Submit a question to compare answers from the raw and clean sources.</span>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="answer-loading" role="status">
        <Icon name="loader" size={17} className="spin" />
        <span>Retrieving context and generating both answers…</span>
      </div>
    );
  }

  if (!response) return null;

  return (
    <div className="answer-results" aria-live="polite">
      <p className="asked-question"><span>Question</span>{question}</p>
      <div className="answer-grid">
        <AnswerCard title="Raw source" side={response.raw} accent="raw" />
        <AnswerCard title="Clean source" side={response.clean} accent="clean" />
      </div>
    </div>
  );
}
