// src/app/models/types.ts

// ── Evento (entidade central) ─────────────────────────────────────────────────

export interface RelacaoEvento {
  id: number;
  origem_id: number;
  destino_id: number;
  intensidade: number;       // 0.0–1.0
  confiabilidade: number;    // 0.0–1.0 (1.0 = manual)
  motivo: string | null;
  criado_em: string;
  outro_evento_id: number | null;
  outro_evento_label: string | null;
  outro_evento_data_hora: string | null;
}

export interface RelacaoCriar {
  evento_id: number;
  intensidade: number;
  confiabilidade: number;
}

export interface Evento {
  id: number;
  evento: string;
  data_hora: string;
  energia: number;
  humor: number;
  estresse: number;
  sensibilidade: number;
  serenidade: number;
  interesse: number;
  descricao: string | null;
  contexto: Record<string, string> | null;
  tags: string[] | null;
  dimensoes_extras: Record<string, number> | null;
  hora: number | null;
  dia_semana: number | null;
  sentimento_score: number | null;
  relacoes_contagem: number;
  relacoes?: RelacaoEvento[];
  criado_em: string;
}

export interface EventoCriar {
  evento: string;
  data_hora?: string | null;
  energia: number;
  humor: number;
  estresse: number;
  sensibilidade: number;
  serenidade: number;
  interesse: number;
  descricao?: string | null;
  contexto?: Record<string, string> | null;
  tags?: string[] | null;
  dimensoes_extras?: Record<string, number> | null;
  relacoes?: Array<{ evento_id: number; intensidade: number; confiabilidade: number }> | null;
}

export interface EventoAtualizar {
  evento?: string;
  data_hora?: string | null;
  energia?: number;
  humor?: number;
  estresse?: number;
  sensibilidade?: number;
  serenidade?: number;
  interesse?: number;
  descricao?: string | null;
  contexto?: Record<string, string> | null;
  tags?: string[] | null;
  dimensoes_extras?: Record<string, number> | null;
}

// ── Preset ────────────────────────────────────────────────────────────────────

export interface Preset {
  label: string;
  energia: number;
  humor: number;
  estresse: number;
  sensibilidade: number;
  serenidade: number;
  interesse: number;
  dimensoes_extras?: Record<string, number> | null;
}

// ── Estado Agregado ───────────────────────────────────────────────────────────

export interface EstadoAgregado {
  data: string;
  energia: number | null;
  humor: number | null;
  estresse: number | null;
  sensibilidade: number | null;
  serenidade: number | null;
  interesse: number | null;
  total_eventos: number;
}

// ── Grafo ──────────────────────────────────────────────────────────────────────

export interface GrafoNo {
  id: number;
  label: string;
  group: string;
  color: string;
  title: string;
  evento: string;
  timestamp: string;
  energia: number;
  humor: number;
  estresse: number;
  sensibilidade: number;
  serenidade: number;
  interesse: number;
  relacoes_contagem: number;
  size?: number;
}

export interface GrafoAresta {
  id: number;
  from: number;
  to: number;
  label: string;
  value: number;
  intensidade: number;
  confiabilidade: number;
  motivo: string | null;
  color?: { color: string; opacity: number };
  width?: number;
  dashes?: boolean;
}

export interface GrafoDados {
  nodes: GrafoNo[];
  edges: GrafoAresta[];
  total_nos: number;
  total_arestas: number;
  evento_central?: number;
  profundidade?: number;
}

// ── Dashboard ──────────────────────────────────────────────────────────────────

export interface ResumoDashboard {
  periodo_dias: number;
  total_eventos: number;
  media_energia: number | null;
  media_humor: number | null;
  media_estresse: number | null;
  media_sensibilidade: number | null;
  media_serenidade: number | null;
  media_interesse: number | null;
  top_eventos: Array<{ nome: string; total: number }>;
}

export interface Streak {
  streak_atual: number;
  streak_maximo: number;
}

// ── Insights ───────────────────────────────────────────────────────────────────

export interface Correlacao {
  dimensao_a: string;
  dimensao_b: string;
  coeficiente: number;
  intensidade: string;
  direcao: string;
  interpretacao: string;
  total_pontos: number;
}

export interface Padrao {
  tipo: string;
  titulo: string;
  descricao: string;
  dados: Record<string, unknown>;
  relevancia: number;
}

export interface Recomendacao {
  categoria: string;
  titulo: string;
  descricao: string;
  prioridade: 'alta' | 'media' | 'baixa';
}
