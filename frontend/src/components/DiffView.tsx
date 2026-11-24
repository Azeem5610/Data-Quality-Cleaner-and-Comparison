import type { ReactNode } from "react";
import type { ProcessResponse, RemovedSegment } from "../types";
import { categoryClass, categoryNames } from "./JunkScoreCard";

interface DiffViewProps {
  result: ProcessResponse;
}

function annotatedText(raw: string, segments: RemovedSegment[]): ReactNode[] {
  const nodes: ReactNode[] = [];
  let cursor = 0;
  const sorted = [...segments].sort((a, b) => a.start - b.start || a.end - b.end);

  for (const segment of sorted) {
    const start = Math.max(cursor, Math.min(raw.length, segment.start));
    const end = Math.max(start, Math.min(raw.length, segment.end));
    if (start > cursor) nodes.push(<span key={`text-${cursor}`}>{raw.slice(cursor, start)}</span>);
    if (end > start) {
      nodes.push(
        <mark className={`removed-mark ${categoryClass(segment.category)}`} title={`Removed: ${categoryNames[segment.category] ?? segment.category}`} key={`removed-${start}-${end}`}>
          {raw.slice(start, end)}
        </mark>,
      );
      cursor = end;
    }
  }
  if (cursor < raw.length) nodes.push(<span key={`text-${cursor}`}>{raw.slice(cursor)}</span>);
  return nodes;
}

export function DiffView({ result }: DiffViewProps) {
  const categories = [...new Set(result.removed_segments.map((segment) => segment.category))];

  return (
    <section className="panel diff-panel" aria-labelledby="diff-title">
      <div className="panel-heading diff-heading">
        <div>
          <div className="eyebrow">Text comparison</div>
          <h2 id="diff-title">What changed</h2>
          <p>Removed segments are highlighted in the original text.</p>
        </div>
        <div className="diff-legend" aria-label="Removal categories">
          {categories.slice(0, 5).map((category) => (
            <span className="legend-item" key={category}>
              <span className={`category-mark ${categoryClass(category)}`} />
              {categoryNames[category] ?? category.replace(/_/g, " ")}
            </span>
          ))}
          {categories.length > 5 && <span className="legend-more">+{categories.length - 5}</span>}
        </div>
      </div>
      <div className="diff-columns">
        <article className="diff-column">
          <header className="diff-column-header">
            <span className="diff-label"><span className="source-indicator raw-indicator" /> Raw source</span>
            <span className="diff-meta">{result.raw_text.length.toLocaleString()} characters</span>
          </header>
          <div className="diff-text raw-text" tabIndex={0} aria-label="Original source text with removed passages highlighted">
            {result.raw_text ? annotatedText(result.raw_text, result.removed_segments) : <span className="text-placeholder">No text was extracted from this source.</span>}
          </div>
        </article>
        <article className="diff-column">
          <header className="diff-column-header">
            <span className="diff-label"><span className="source-indicator clean-indicator" /> Clean source</span>
            <span className="diff-meta">{result.clean_text.length.toLocaleString()} characters</span>
          </header>
          <div className="diff-text clean-text" tabIndex={0} aria-label="Cleaned source text">
            {result.clean_text || <span className="text-placeholder">The cleaner did not return any text.</span>}
          </div>
        </article>
      </div>
    </section>
  );
}
