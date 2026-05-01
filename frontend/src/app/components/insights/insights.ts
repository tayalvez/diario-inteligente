// src/app/components/insights/insights.ts
import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { firstValueFrom } from 'rxjs';
import { ApiService } from '../../services/api';
import { Correlacao, Padrao, Recomendacao } from '../../models/types';

@Component({
  selector: 'app-insights',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './insights.html',
  styleUrl: './insights.css'
})
export class InsightsComponent implements OnInit {
  carregando = true;
  correlacoes: Correlacao[] = [];
  padroes: Padrao[] = [];
  comportamentais: Padrao[] = [];
  recomendacoes: Recomendacao[] = [];
  insightHub: any = null;
  insightEvolucao: any = null;
  insightCluster: any = null;
  qualidadeRelacoes: any = null;
  perceptionBias: any = null;
  mensagemCorrelacao = '';
  totalEventos = 0;
  toast: { mensagem: string; tipo: string } | null = null;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.carregarInsights();
  }

  atualizarInsights(): void {
    this.carregarInsights();
  }

  carregarInsights(): void {
    this.carregando = true;

    Promise.all([
      firstValueFrom(this.api.correlacoes(60)),
      firstValueFrom(this.api.padroes(60)),
      firstValueFrom(this.api.recomendacoes()),
      firstValueFrom(this.api.comportamentais(60)),
      firstValueFrom(this.api.insightsRelacoes(60)),
      firstValueFrom(this.api.qualidadeRelacoes(60)),
      firstValueFrom(this.api.perceptionBias(60)),
    ]).then(([corr, pad, rec, comp, rel, qual, bias]) => {
      this.correlacoes = (corr?.correlacoes || []).slice(0, 8);
      this.mensagemCorrelacao = corr?.mensagem || '';
      this.totalEventos = corr?.total_eventos || 0;
      this.padroes = pad?.padroes || [];
      this.recomendacoes = rec?.recomendacoes || [];
      this.comportamentais = comp?.padroes || [];
      this.insightHub = rel?.hub || null;
      this.insightEvolucao = rel?.evolucao || null;
      this.insightCluster = rel?.cluster || null;
      this.qualidadeRelacoes = qual || null;
      this.perceptionBias = bias || null;
      this.carregando = false;
      this.cdr.detectChanges();
    }).catch(() => {
      this.mostrarToast('Erro ao carregar insights', 'error');
      this.carregando = false;
      this.cdr.detectChanges();
    });
  }

  larguraCorrelacao(coeficiente: number): number {
    return Math.abs(coeficiente) * 100;
  }

  corCorrelacao(coeficiente: number): string {
    return coeficiente > 0 ? '#5dc893' : '#e07da8';
  }

  corPrioridade(p: string): string {
    const map: Record<string, string> = { alta: '#e07da8', media: '#ddc346', baixa: '#7eb8e8' };
    return map[p] || '#c5b8f0';
  }

  mostrarToast(mensagem: string, tipo: string): void {
    this.toast = { mensagem, tipo };
    setTimeout(() => this.toast = null, 3500);
  }

  pct(valor: number): string {
    return `${Math.round((valor || 0) * 100)}%`;
  }

  larguraPct(valor: number): string {
    return `${Math.max(2, Math.round((valor || 0) * 100))}%`;
  }
}
