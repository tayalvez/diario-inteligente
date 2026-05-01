// src/app/components/dashboard/dashboard.ts
import { Component, OnInit, ChangeDetectorRef, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api';
import { EstadoAgregado } from '../../models/types';
import { HistoricoModalComponent } from '../historico-modal/historico-modal';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule, FormsModule, HistoricoModalComponent],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.css'
})
export class DashboardComponent implements OnInit {
  @ViewChild('historicoModal') historicoModal!: HistoricoModalComponent;

  periodo = 30;
  saudacao = '';
  datahoje = '';
  streakAtual = 0;
  streakMaximo = 0;

  resumo: any = null;
  estadoHoje: EstadoAgregado | null = null;
  carregando = true;

  toast: { mensagem: string; tipo: string } | null = null;

  constructor(private api: ApiService, private cdr: ChangeDetectorRef) {}

  ngOnInit(): void {
    this.inicializarData();
    this.carregarDados();
  }

  private inicializarData(): void {
    const hora = new Date().getHours();
    if (hora < 12)       this.saudacao = 'Bom dia!';
    else if (hora < 18)  this.saudacao = 'Boa tarde!';
    else                 this.saudacao = 'Boa noite!';

    const opts: Intl.DateTimeFormatOptions = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const d = new Date().toLocaleDateString('pt-BR', opts);
    this.datahoje = d.charAt(0).toUpperCase() + d.slice(1);
  }

  carregarDados(): void {
    this.carregando = true;

    this.api.resumoCompleto(this.periodo).subscribe({
      next: (r) => {
        this.resumo       = r;
        this.streakAtual  = r.streak_atual;
        this.streakMaximo = r.streak_maximo;
        this.estadoHoje   = r.estado_hoje;
        this.carregando   = false;
        this.cdr.detectChanges();
      },
      error: () => { this.carregando = false; this.cdr.detectChanges(); }
    });
  }

  mudarPeriodo(dias: number): void {
    this.periodo = dias;
    this.carregarDados();
  }

  abrirHistorico(): void { this.historicoModal.abrir(); }

  exibir(v: number | null): string {
    if (v === null || v === undefined) return '—';
    return (v * 10).toFixed(1).replace('.0', '');
  }

  barWidth(v: number | null): string {
    return v !== null ? `${Math.round(v * 100)}%` : '0%';
  }

  mostrarToast(mensagem: string, tipo: string): void {
    this.toast = { mensagem, tipo };
    setTimeout(() => this.toast = null, 3500);
  }
}
