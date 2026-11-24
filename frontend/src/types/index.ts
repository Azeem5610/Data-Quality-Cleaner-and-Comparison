// Mirrors backend/src/schemas.py. Keep in sync.

export interface PageText {
  page_number: number;
  text: string;
}

export interface RemovedSegment {
  text: string;
  category: string;
  start: number; // offset into raw_text (inclusive)
  end: number; // offset into raw_text (exclusive)
}

export interface ProcessResponse {
  source_id: string;
  source_name: string;
  source_type: "pdf" | "web";
  raw_text: string;
  clean_text: string;
  removed_segments: RemovedSegment[];
  junk_score: number; // 0.0 - 1.0
  breakdown: Record<string, number>;
  summary: string;
  pages?: PageText[] | null;
  raw_html?: string | null;
}

export interface AskRequest {
  source_id: string;
  question: string;
}

export interface RetrievedChunk {
  text: string;
  chunk_index: number;
  start: number;
  end: number;
}

export interface AskSideResponse {
  answer: string;
  chunks: RetrievedChunk[];
}

export interface AskResponse {
  raw: AskSideResponse;
  clean: AskSideResponse;
}

export interface SampleSource {
  name: string;
  label: string;
}
