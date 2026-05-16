import { api } from "./client";

export interface QACitation {
  documant_id: string;
  doc_title: string;
  chunk_text: string;
  score: number;
}

export interface QAResponse {
  question: string;
  answer: string;
  citations: QACitation[];
  model: string;
}

export function askQuestion(question: string, top_k = 5): Promise<QAResponse> {
  return api.post<QAResponse>("/qa", { question, top_k });
}
