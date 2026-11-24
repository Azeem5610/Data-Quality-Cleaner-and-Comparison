import { useState, type FormEvent } from "react";
import { Icon } from "./Icon";

interface AskPanelProps {
  disabled: boolean;
  loading: boolean;
  onAsk: (question: string) => void;
}

export function AskPanel({ disabled, loading, onAsk }: AskPanelProps) {
  const [question, setQuestion] = useState("");

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || disabled || loading) return;
    onAsk(trimmed);
  }

  return (
    <div className="ask-form-wrap">
      <div>
        <div className="eyebrow">Ask both versions</div>
        <h2 id="answers-title">Compare answers</h2>
        <p>See how the retrieved context changes after cleaning.</p>
      </div>
      <form className="ask-form" onSubmit={submit}>
        <label className="visually-hidden" htmlFor="question-input">Question to compare</label>
        <input
          id="question-input"
          type="text"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask a question about this source…"
          maxLength={2000}
          disabled={disabled || loading}
        />
        <button className="button button-primary" type="submit" disabled={disabled || loading || !question.trim()}>
          {loading ? <><Icon name="loader" size={16} className="spin" /> Comparing</> : <><Icon name="arrow" size={16} /> Compare answers</>}
        </button>
      </form>
      {disabled && <p className="ask-hint">Analyze a source to ask a question.</p>}
    </div>
  );
}
