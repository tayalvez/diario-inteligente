import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../../services/api';
import { Evento, EstadoAgregado } from '../../models/types';

@Component({
  selector: 'app-historico-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './historico-modal.html',
  styleUrl: './historico-modal.css',
})
export class HistoricoModalComponent {
  aberto = false;
  historico: EstadoAgregado[] = [];
  eventos: Evento[] = [];
  diasHistorico = 30;
  tabelaExpandida = false;
  visao: 'dia' | 'evento' = 'dia';
  private chart: any = null;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  abrir(): void {
    this.aberto = true;
    this.tabelaExpandida = false;
    this.carregar();
  }

  fechar(): void {
    if (this.chart) { this.chart.destroy(); this.chart = null; }
    this.aberto = false;
  }

  alternarVisao(v: 'dia' | 'evento'): void {
    if (this.visao === v) return;
    if (this.chart) { this.chart.destroy(); this.chart = null; }
    this.visao = v;
    this.carregar();
  }

  carregar(): void {
    if (this.visao === 'dia') {
      this.api.historicoEstado(this.diasHistorico).subscribe({
        next: h => { this.historico = h; this.cdr.detectChanges(); setTimeout(() => this.renderizarDia(), 50); },
      });
    } else {
      this.api.listarEventos({ dias: this.diasHistorico, limite: 500 }).subscribe({
        next: evts => {
          this.eventos = evts.slice().reverse();
          this.cdr.detectChanges();
          setTimeout(() => this.renderizarEvento(), 50);
        },
      });
    }
  }

  private renderizarDia(): void {
    const canvas = document.getElementById('grafico-historico-dia') as HTMLCanvasElement;
    if (!canvas || !(window as any).Chart) return;
    if (this.chart) { this.chart.destroy(); this.chart = null; }

    const labels = this.historico.map(e => {
      const d = new Date(e.data + 'T00:00:00');
      return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
    });

    this.chart = new (window as any).Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Humor',         data: this.historico.map(e => e.humor         !== null ? Math.round(e.humor         * 10) : null), borderColor: '#D88C9A', tension: 0.4, fill: false, pointRadius: 4 },
          { label: 'Energia',       data: this.historico.map(e => e.energia       !== null ? Math.round(e.energia       * 10) : null), borderColor: '#7FA87F', tension: 0.4, fill: false, pointRadius: 4 },
          { label: 'Estresse',      data: this.historico.map(e => e.estresse      !== null ? Math.round(e.estresse      * 10) : null), borderColor: '#C75C5C', tension: 0.4, fill: false, pointRadius: 4 },
          { label: 'Sensibilidade', data: this.historico.map(e => e.sensibilidade !== null ? Math.round(e.sensibilidade * 10) : null), borderColor: '#B07FBF', tension: 0.4, fill: false, pointRadius: 4 },
          { label: 'Serenidade',    data: this.historico.map(e => e.serenidade    !== null ? Math.round(e.serenidade    * 10) : null), borderColor: '#5BAAB0', tension: 0.4, fill: false, pointRadius: 4 },
          { label: 'Interesse',     data: this.historico.map(e => e.interesse     !== null ? Math.round(e.interesse     * 10) : null), borderColor: '#D4A84B', tension: 0.4, fill: false, pointRadius: 4 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          y: { min: 0, max: 10, grid: { color: '#EDE4D8' }, ticks: { font: { family: 'Nunito' } } },
          x: { grid: { color: '#EDE4D8' }, ticks: { font: { family: 'Nunito' } } },
        },
        plugins: { legend: { labels: { font: { family: 'Nunito', weight: '700' } } } },
      },
    });
  }

  private renderizarEvento(): void {
    const canvas = document.getElementById('grafico-historico-evento') as HTMLCanvasElement;
    if (!canvas || !(window as any).Chart) return;
    if (this.chart) { this.chart.destroy(); this.chart = null; }

    const labels = this.eventos.map(e => {
      const d = new Date(e.data_hora);
      return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }) + ' '
           + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
    });

    const evts = this.eventos;
    this.chart = new (window as any).Chart(canvas, {
      type: 'line',
      data: {
        labels,
        datasets: [
          { label: 'Humor',         data: evts.map(e => Math.round(e.humor         * 10)), borderColor: '#D88C9A', tension: 0.3, fill: false, pointRadius: 3 },
          { label: 'Energia',       data: evts.map(e => Math.round(e.energia       * 10)), borderColor: '#7FA87F', tension: 0.3, fill: false, pointRadius: 3 },
          { label: 'Estresse',      data: evts.map(e => Math.round(e.estresse      * 10)), borderColor: '#C75C5C', tension: 0.3, fill: false, pointRadius: 3 },
          { label: 'Sensibilidade', data: evts.map(e => Math.round(e.sensibilidade * 10)), borderColor: '#B07FBF', tension: 0.3, fill: false, pointRadius: 3 },
          { label: 'Serenidade',    data: evts.map(e => Math.round(e.serenidade    * 10)), borderColor: '#5BAAB0', tension: 0.3, fill: false, pointRadius: 3 },
          { label: 'Interesse',     data: evts.map(e => Math.round(e.interesse     * 10)), borderColor: '#D4A84B', tension: 0.3, fill: false, pointRadius: 3 },
        ],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        scales: {
          y: { min: 0, max: 10, grid: { color: '#EDE4D8' }, ticks: { font: { family: 'Nunito' } } },
          x: { grid: { color: '#EDE4D8' }, ticks: { font: { family: 'Nunito' }, maxTicksLimit: 12 } },
        },
        plugins: {
          legend: { labels: { font: { family: 'Nunito', weight: '700' } } },
          tooltip: {
            callbacks: {
              title: (items: any[]) => {
                const idx = items[0]?.dataIndex;
                const evt = evts[idx];
                return evt ? `${evt.evento} — ${labels[idx]}` : labels[idx];
              },
            },
          },
        },
      },
    });
  }

  exibir(v: number | null): string {
    if (v === null || v === undefined) return '—';
    return (v * 10).toFixed(1).replace('.0', '');
  }

  formatarDataHora(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })
         + ' ' + d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' });
  }
}
