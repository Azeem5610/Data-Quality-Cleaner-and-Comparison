import type { ProcessResponse } from "../types";

interface JunkScoreCardProps {
  result: ProcessResponse;
}

const categoryNames: Record<string, string> = {
  header_footer: "Header / footer",
  page_number: "Page numbers",
  navigation: "Navigation",
  cookie_consent: "Cookie consent",
  boilerplate: "Boilerplate",
  duplicate: "Duplicate text",
  whitespace: "Whitespace",
};

function categoryClass(category: string) {
  return `category-${category.replace(/[^a-z0-9_-]/gi, "-")}`;
}

export function JunkScoreCard({ result }: JunkScoreCardProps) {
  const categories = Object.entries(result.breakdown).sort((a, b) => b[1] - a[1]);
  const total = categories.reduce((sum, [, value]) => sum + Math.max(0, value), 0);

  return (
    <section className="panel report-panel" aria-labelledby="report-title">
      <div className="panel-heading report-heading">
        <div>
          <div className="eyebrow">Quality report</div>
          <h2 id="report-title">Source noise</h2>
        </div>
        <div className="report-caption">Removed text by category</div>
      </div>
      <div className="report-content">
        <div className="score-block">
          <div className="score-number">{(result.junk_score * 100).toFixed(1)}<span>%</span></div>
          <div className="score-label">of source text removed</div>
          <p className="report-summary">{result.summary}</p>
        </div>
        <div className="breakdown-list">
          {categories.length === 0 ? (
            <div className="breakdown-empty">No removable text was detected.</div>
          ) : categories.map(([category, value]) => {
            const share = total > 0 ? value / total : 0;
            return (
              <div className="breakdown-row" key={category}>
                <div className="breakdown-label-row">
                  <span className={`category-mark ${categoryClass(category)}`} />
                  <span className="breakdown-label">{categoryNames[category] ?? category.replace(/_/g, " ")}</span>
                  <span className="breakdown-value">{(share * 100).toFixed(0)}%</span>
                </div>
                <div className="breakdown-track" aria-label={`${categoryNames[category] ?? category}: ${(share * 100).toFixed(0)} percent of removed text`}>
                  <span className={`breakdown-fill ${categoryClass(category)}`} style={{ width: `${Math.max(0, Math.min(100, share * 100))}%` }} />
                </div>
              </div>
            );
          })}
          {categories.length > 0 && <div className="breakdown-footnote">Share of removed text</div>}
        </div>
      </div>
    </section>
  );
}

export { categoryClass, categoryNames };
