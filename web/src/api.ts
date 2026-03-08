/**
 * API client for Lead Scoring demo backend.
 */

export interface DataRow {
  row: number;
  [key: string]: unknown;
}

export interface PreviewResponse {
  rows: DataRow[];
  page: number;
  page_size: number;
  total_rows: number;
  total_pages: number;
}

export interface Prediction {
  row: number;
  label: number | null;
  score_focus_c: number;
  score_focus_e: number;
}

export interface PredictResponse {
  predictions: Prediction[];
}

export interface GlossaryColumn {
  name: string;
  description: string;
  displayName?: string;
}

export interface Glossary {
  columns: GlossaryColumn[];
  metrics: { name: string; description: string }[];
  focusExplanation: string;
  areaProfileExplanation?: string;
}

const API_BASE = '/api';

export async function fetchPreview(page = 1, pageSize = 50): Promise<PreviewResponse> {
  const res = await fetch(`${API_BASE}/data/preview?page=${page}&page_size=${pageSize}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchRow(rowNum: number): Promise<DataRow> {
  const res = await fetch(`${API_BASE}/data/row/${rowNum}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function predict(rowNumbers: number[]): Promise<PredictResponse> {
  const res = await fetch(`${API_BASE}/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ row_numbers: rowNumbers }),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function fetchGlossary(): Promise<Glossary> {
  const res = await fetch(`${API_BASE}/glossary`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
