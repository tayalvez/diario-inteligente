// src/app/services/api.ts
import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  Evento, EventoCriar, EventoAtualizar,
  RelacaoEvento, RelacaoCriar,
  Preset, EstadoAgregado,
  GrafoDados,
  ResumoDashboard, Streak,
  Correlacao, Padrao, Recomendacao,
} from '../models/types';

const API = '';

@Injectable({ providedIn: 'root' })
export class ApiService {
  constructor(private http: HttpClient) {}

  // ── Presets ────────────────────────────────────────────────────────────────

  listarPresets(): Observable<Preset[]> {
    return this.http.get<Preset[]>(`${API}/api/eventos/presets`);
  }

  // ── Eventos ────────────────────────────────────────────────────────────────

  listarEventos(params?: { dias?: number; limite?: number; include_relacoes?: boolean }): Observable<Evento[]> {
    let q = new HttpParams().set('_t', Date.now().toString());
    if (params?.dias) q = q.set('dias', String(params.dias));
    if (params?.limite) q = q.set('limite', String(params.limite));
    if (params?.include_relacoes) q = q.set('include_relacoes', 'true');
    return this.http.get<Evento[]>(`${API}/api/eventos/`, { params: q });
  }

  obterEvento(id: number): Observable<Evento> {
    return this.http.get<Evento>(`${API}/api/eventos/${id}?include_relacoes=true`);
  }

  criarEvento(dados: EventoCriar): Observable<Evento> {
    return this.http.post<Evento>(`${API}/api/eventos/`, dados);
  }

  atualizarEvento(id: number, dados: EventoAtualizar): Observable<Evento> {
    return this.http.put<Evento>(`${API}/api/eventos/${id}`, dados);
  }

  excluirEvento(id: number): Observable<any> {
    return this.http.delete(`${API}/api/eventos/${id}`, { responseType: 'text' });
  }

  // ── Estado agregado ────────────────────────────────────────────────────────

  estadoHoje(): Observable<EstadoAgregado | null> {
    const q = new HttpParams().set('_t', Date.now().toString());
    return this.http.get<EstadoAgregado | null>(`${API}/api/eventos/estado-hoje`, { params: q });
  }

  historicoEstado(dias = 30): Observable<EstadoAgregado[]> {
    const q = new HttpParams()
      .set('dias', String(dias))
      .set('_t', Date.now().toString());
    return this.http.get<EstadoAgregado[]>(`${API}/api/eventos/historico`, { params: q });
  }

  // ── Relações ───────────────────────────────────────────────────────────────

  listarRelacoes(eventoId: number): Observable<RelacaoEvento[]> {
    return this.http.get<RelacaoEvento[]>(`${API}/api/eventos/${eventoId}/relacoes`);
  }

  criarRelacao(eventoId: number, dados: RelacaoCriar): Observable<RelacaoEvento> {
    return this.http.post<RelacaoEvento>(`${API}/api/eventos/${eventoId}/relacoes`, dados);
  }

  excluirRelacao(relacaoId: number): Observable<any> {
    return this.http.delete(`${API}/api/eventos/relacoes/${relacaoId}`, { responseType: 'text' });
  }

  sugerirRelacionados(eventoId: number, horas = 48): Observable<Evento[]> {
    return this.http.get<Evento[]>(`${API}/api/eventos/${eventoId}/sugestoes?horas=${horas}`);
  }

  // ── Grafo ──────────────────────────────────────────────────────────────────

  grafoGlobal(params?: { data_inicio?: string; data_fim?: string; limite?: number }): Observable<GrafoDados> {
    let q = new HttpParams().set('_t', Date.now().toString());
    if (params?.data_inicio) q = q.set('data_inicio', params.data_inicio);
    if (params?.data_fim) q = q.set('data_fim', params.data_fim);
    if (params?.limite) q = q.set('limite', String(params.limite));
    return this.http.get<GrafoDados>(`${API}/api/grafo/`, { params: q });
  }

  grafoLocal(eventoId: number, profundidade = 2): Observable<GrafoDados> {
    const q = new HttpParams()
      .set('profundidade', String(profundidade))
      .set('_t', Date.now().toString());
    return this.http.get<GrafoDados>(`${API}/api/grafo/${eventoId}`, { params: q });
  }

  // ── Dashboard ──────────────────────────────────────────────────────────────

  resumoDashboard(dias = 30): Observable<ResumoDashboard> {
    const q = new HttpParams()
      .set('dias', String(dias))
      .set('_t', Date.now().toString());
    return this.http.get<ResumoDashboard>(`${API}/api/dashboard/resumo`, { params: q });
  }

  resumoCompleto(dias = 30): Observable<ResumoDashboard & { estado_hoje: any; streak_atual: number; streak_maximo: number }> {
    const q = new HttpParams()
      .set('dias', String(dias))
      .set('_t', Date.now().toString());
    return this.http.get<any>(`${API}/api/dashboard/resumo-completo`, { params: q });
  }

  streak(): Observable<Streak> {
    const q = new HttpParams().set('_t', Date.now().toString());
    return this.http.get<Streak>(`${API}/api/dashboard/streak`, { params: q });
  }

  // ── Insights ───────────────────────────────────────────────────────────────

  correlacoes(dias = 60): Observable<{ correlacoes: Correlacao[]; total_eventos: number; mensagem: string }> {
    const q = new HttpParams()
      .set('dias', String(dias))
      .set('_t', Date.now().toString());
    return this.http.get<any>(`${API}/api/insights/correlacoes`, { params: q });
  }

  padroes(dias = 60): Observable<{ padroes: Padrao[]; total: number }> {
    const q = new HttpParams()
      .set('dias', String(dias))
      .set('_t', Date.now().toString());
    return this.http.get<any>(`${API}/api/insights/padroes`, { params: q });
  }

  recomendacoes(): Observable<{ recomendacoes: Recomendacao[]; baseado_em_eventos: number }> {
    const q = new HttpParams().set('_t', Date.now().toString());
    return this.http.get<any>(`${API}/api/insights/recomendacoes`, { params: q });
  }

  comportamentais(dias = 60): Observable<{ padroes: Padrao[]; total: number }> {
    const q = new HttpParams()
      .set('dias', String(dias))
      .set('_t', Date.now().toString());
    return this.http.get<any>(`${API}/api/insights/comportamentais`, { params: q });
  }

  insightsRelacoes(dias = 60): Observable<{ hub: any; evolucao: any; cluster: any }> {
    const q = new HttpParams()
      .set('dias', String(dias))
      .set('_t', Date.now().toString());
    return this.http.get<any>(`${API}/api/insights/relacoes-insights`, { params: q });
  }

  qualidadeRelacoes(dias = 60): Observable<any> {
    const q = new HttpParams()
      .set('dias', String(dias))
      .set('_t', Date.now().toString());
    return this.http.get<any>(`${API}/api/insights/qualidade-relacoes`, { params: q });
  }

  perceptionBias(dias = 60): Observable<any> {
    const q = new HttpParams()
      .set('dias', String(dias))
      .set('_t', Date.now().toString());
    return this.http.get<any>(`${API}/api/insights/perception-bias`, { params: q });
  }
}
