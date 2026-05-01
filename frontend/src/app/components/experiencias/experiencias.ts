// src/app/components/experiencias/experiencias.ts
import { Component, OnInit, ChangeDetectorRef, NgZone, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api';
import {
  Preset, Evento, EventoCriar, EventoAtualizar,
  EstadoAgregado, RelacaoEvento,
} from '../../models/types';
import { HistoricoModalComponent } from '../historico-modal/historico-modal';

interface FormEvento {
  evento: string;
  data_hora: string;
  energia: number;
  humor: number;
  estresse: number;
  sensibilidade: number;
  serenidade: number;
  interesse: number;
  descricao: string;
  tags: string;
  contextoChave: string;
  contextoValor: string;
  contextoItens: Array<{ chave: string; valor: string }>;
  dimensoesExtrasNome: string;
  dimensoesExtrasValor: number;
  dimensoesExtras: Record<string, number>;
}

@Component({
  selector: 'app-experiencias',
  standalone: true,
  imports: [CommonModule, FormsModule, HistoricoModalComponent],
  templateUrl: './experiencias.html',
  styleUrl: './experiencias.css',
})
export class ExperienciasComponent implements OnInit {
  @ViewChild('historicoModal') historicoModal!: HistoricoModalComponent;
  presets: Preset[] = [];
  eventos: Evento[] = [];
  estadoHoje: EstadoAgregado | null = null;
  carregando = true;
  toast: { mensagem: string; tipo: string } | null = null;

  modalAberto = false;
  modoEdicao = false;
  editandoId: number | null = null;
  form: FormEvento = this.formVazio();


  confirmandoExclusao: number | null = null;
  nivelForm: 'basico' | 'avancado' = 'basico';

  // ── Tema do caderno ────────────────────────────────────────────────────────
  readonly notebookThemes = [
    { id: 'padrao',    label: 'Padrão',    img: ''                                        },
    { id: 'coelho',    label: 'Coelho',    img: 'assets/backgrounds/back-02-celular.png'  },
    { id: 'tech',      label: 'Tech',      img: 'assets/backgrounds/back-03.png'          },
    { id: 'lilas',     label: 'Lilás',     img: 'assets/backgrounds/background-1.png'     },
    { id: 'estudos',   label: 'Estudos',   img: 'assets/backgrounds/back-08.png'          },
    { id: 'fofinhos',  label: 'Fofinhos',  img: 'assets/backgrounds/back-09.png'          },
    { id: 'sombrio',   label: 'Sombrio',   img: 'assets/backgrounds/back-10.png'          },
  ];

  notebookTheme = localStorage.getItem('notebookTheme') || 'padrao';

  setNotebookTheme(id: string): void {
    this.notebookTheme = id;
    localStorage.setItem('notebookTheme', id);
  }

  getModalBgStyle(): Record<string, string> {
    const t = this.notebookThemes.find(x => x.id === this.notebookTheme);
    if (!t?.img) return {};
    return { 'background-image': `url('${t.img}')` };
  }

  // ── Relações ──────────────────────────────────────────────────────────────
  relacoes: RelacaoEvento[] = [];           // relações existentes (modo edição)

  // modal de relações
  modalRelacoes = false;
  eventoRelacoes: Evento | null = null;
  relacoesPainel: RelacaoEvento[] = [];
  relacoesPainelCarregando = false;
  relacaoExpandidaId: number | null = null;
  sugestoes: Evento[] = [];                 // candidatos para nova relação
  novaRelacaoId: number | null = null;
  novaRelacaoIntensidade = 5;
  relacoesSelecionadas: Array<{ evento_id: number; label: string; intensidade: number }> = [];

  constructor(private api: ApiService, private cdr: ChangeDetectorRef, private zone: NgZone) {}

  ngOnInit(): void {
    this.api.listarPresets().subscribe({ next: p => { this.presets = p; this.cdr.detectChanges(); } });
    this.carregarDados();
  }

  carregarDados(): void {
    this.carregando = true;
    this.api.listarEventos({ limite: 50, include_relacoes: true }).subscribe({
      next: e => { this.eventos = e; this.carregando = false; this.cdr.detectChanges(); },
      error: () => { this.carregando = false; this.cdr.detectChanges(); },
    });
    this.api.estadoHoje().subscribe({
      next: e => { this.estadoHoje = e; this.cdr.detectChanges(); },
    });
  }

  // ── Modal ──────────────────────────────────────────────────────────────���───

  abrirModal(preset?: Preset): void {
    this.modoEdicao = false;
    this.editandoId = null;
    this.nivelForm = 'basico';
    this.form = this.formVazio();
    this.relacoes = [];
    this.relacoesSelecionadas = [];
    this.novaRelacaoId = null;
    this.novaRelacaoIntensidade = 5;
    // Sugestões = anotações já existentes na lista
    this.sugestoes = [...this.eventos];
    if (preset) {
      const meio = (v: number) => Math.round(v * 20) / 2;
      this.form.evento        = preset.label;
      this.form.energia       = meio(preset.energia);
      this.form.humor         = meio(preset.humor);
      this.form.estresse      = meio(preset.estresse);
      this.form.sensibilidade = meio(preset.sensibilidade);
      this.form.serenidade    = meio(preset.serenidade);
      this.form.interesse     = meio(preset.interesse);
    }
    this.modalAberto = true;
  }

  editarEvento(e: Evento): void {
    this.modoEdicao = true;
    this.editandoId = e.id;
    this.nivelForm = (e.descricao || e.tags?.length || e.contexto || e.relacoes_contagem > 0) ? 'avancado' : 'basico';
    const meio = (v: number) => Math.round(v * 20) / 2;
    this.form = {
      evento: e.evento,
      data_hora: this.isoParaLocal(e.data_hora),
      energia:       meio(e.energia),
      humor:         meio(e.humor),
      estresse:      meio(e.estresse),
      sensibilidade: meio(e.sensibilidade),
      serenidade:    meio(e.serenidade),
      interesse:     meio(e.interesse),
      descricao: e.descricao || '',
      tags: e.tags ? e.tags.join(', ') : '',
      contextoChave: '', contextoValor: '',
      contextoItens: e.contexto
        ? Object.entries(e.contexto).map(([chave, valor]) => ({ chave, valor }))
        : [],
      dimensoesExtrasNome: '',
      dimensoesExtrasValor: 5,
      dimensoesExtras: e.dimensoes_extras
        ? Object.fromEntries(Object.entries(e.dimensoes_extras).map(([k, v]) => [k, Math.round(v * 10)]))
        : {},
    };
    this.relacoes = [];
    this.sugestoes = [];
    this.novaRelacaoId = null;
    this.carregarRelacoes(e.id);
    this.modalAberto = true;
  }

  fecharModal(): void {
    this.zone.run(() => {
      this.modalAberto = false;
      this.cdr.detectChanges();
    });
  }

  // ── Relações ──────────────────────────────────────────────────────��────────

  carregarRelacoes(id: number): void {
    this.api.listarRelacoes(id).subscribe({
      next: r => {
        this.relacoes = r;
        this.reconstruirSugestoes(id);
        this.cdr.detectChanges();
      },
    });
  }

  private reconstruirSugestoes(id: number): void {
    const relIds = new Set(this.relacoes.map(r => r.outro_evento_id).filter((x): x is number => x !== null));
    this.sugestoes = this.eventos.filter(e => e.id !== id && !relIds.has(e.id));
  }

  adicionarRelacao(): void {
    if (!this.novaRelacaoId) return;

    if (this.modoEdicao && this.editandoId) {
      // Edição: cria direto na API
      this.api.criarRelacao(this.editandoId, {
        evento_id: this.novaRelacaoId,
        intensidade: this.novaRelacaoIntensidade / 10,
        confiabilidade: 1.0,
      }).subscribe({
        next: () => {
          this.novaRelacaoId = null;
          this.novaRelacaoIntensidade = 5;
          this.carregarRelacoes(this.editandoId!);
          this.notificarAtualizacaoDados();
          this.mostrarToast('Relação adicionada!', 'success');
        },
        error: e => this.mostrarToast(e.error?.detail || 'Erro ao relacionar', 'error'),
      });
    } else {
      // Criação: guarda como pendente
      const id = Number(this.novaRelacaoId);
      const alvo = this.sugestoes.find(s => s.id === id);
      if (!alvo) { this.mostrarToast('Anotação não encontrada', 'error'); return; }
      const jaExiste = this.relacoesSelecionadas.some(r => r.evento_id === id);
      if (jaExiste) { this.mostrarToast('Relação já adicionada', 'error'); return; }
      this.relacoesSelecionadas.push({
        evento_id: id,
        label: alvo.evento,
        intensidade: this.novaRelacaoIntensidade,
      });
      this.novaRelacaoId = null;
      this.novaRelacaoIntensidade = 5;
      this.cdr.detectChanges();
    }
  }

  removerRelacao(relacaoId: number): void {
    this.api.excluirRelacao(relacaoId).subscribe({
      next: () => {
        this.relacoes = this.relacoes.filter(r => r.id !== relacaoId);
        if (this.editandoId) this.reconstruirSugestoes(this.editandoId);
        this.notificarAtualizacaoDados();
        this.cdr.detectChanges();
      },
      error: () => this.mostrarToast('Erro ao remover relação', 'error'),
    });
  }

  removerRelacaoPendente(eventoId: number): void {
    this.relacoesSelecionadas = this.relacoesSelecionadas.filter(r => r.evento_id !== eventoId);
  }

  labelRelacao(r: RelacaoEvento): string {
    const outro = r.outro_evento_label ?? `#${r.outro_evento_id}`;
    return outro;
  }

  dataRelacao(r: RelacaoEvento): string {
    if (!r.outro_evento_data_hora) return '';
    return new Date(r.outro_evento_data_hora).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' });
  }

  abrirModalRelacoes(e: Evento): void {
    this.eventoRelacoes = e;
    this.relacoesPainel = e.relacoes || [];
    this.relacoesPainelCarregando = false;
    this.modalRelacoes = true;
  }

  fecharModalRelacoes(): void {
    this.modalRelacoes = false;
    this.eventoRelacoes = null;
    this.relacoesPainel = [];
    this.relacaoExpandidaId = null;
  }

  toggleRelacaoMotivo(id: number): void {
    this.relacaoExpandidaId = this.relacaoExpandidaId === id ? null : id;
  }

  forcaRelacao(r: RelacaoEvento): number {
    const numMotivos = r.motivo ? r.motivo.split('; ').length : 0;
    const bonus = 1 + 0.1 * Math.max(0, numMotivos - 1);
    return +(Math.min(1.0, r.intensidade * r.confiabilidade * bonus) * 10).toFixed(1);
  }

  // ── Contexto / dimensões extras ────────────────────────────────────────────

  adicionarContexto(): void {
    if (!this.form.contextoChave.trim()) return;
    this.form.contextoItens.push({ chave: this.form.contextoChave.trim(), valor: this.form.contextoValor.trim() });
    this.form.contextoChave = '';
    this.form.contextoValor = '';
  }

  removerContexto(i: number): void { this.form.contextoItens.splice(i, 1); }

  adicionarDimensaoExtra(): void {
    const nome = this.form.dimensoesExtrasNome.trim();
    if (!nome) return;
    this.form.dimensoesExtras[nome] = this.form.dimensoesExtrasValor;
    this.form.dimensoesExtrasNome = '';
    this.form.dimensoesExtrasValor = 5;
  }

  removerDimensaoExtra(nome: string): void { delete this.form.dimensoesExtras[nome]; }

  // ── Salvar ─────────────────────────────────────────────────────────────────

  salvar(): void {
    if (!this.form.evento.trim()) { this.mostrarToast('Informe a anotação', 'error'); return; }

    const norm = (v: number) => Math.round(v * 10) / 100;
    const contexto = this.form.contextoItens.length
      ? Object.fromEntries(this.form.contextoItens.map(i => [i.chave, i.valor])) : null;
    const tags = this.form.tags.trim()
      ? this.form.tags.split(',').map(t => t.trim()).filter(Boolean) : null;
    const dimensoesExtras = Object.keys(this.form.dimensoesExtras).length
      ? Object.fromEntries(Object.entries(this.form.dimensoesExtras).map(([k, v]) => [k, norm(v)])) : null;

    const payload: EventoCriar = {
      evento: this.form.evento.trim().toLowerCase(),
      data_hora: this.form.data_hora ? this.form.data_hora + ':00' : undefined,
      energia: norm(this.form.energia), humor: norm(this.form.humor), estresse: norm(this.form.estresse),
      sensibilidade: norm(this.form.sensibilidade), serenidade: norm(this.form.serenidade), interesse: norm(this.form.interesse),
      descricao: this.form.descricao?.trim() || null,
      contexto, tags, dimensoes_extras: dimensoesExtras,
      relacoes: !this.modoEdicao && this.relacoesSelecionadas.length
        ? this.relacoesSelecionadas.map(r => ({ evento_id: r.evento_id, intensidade: r.intensidade / 10, confiabilidade: 1.0 }))
        : null,
    };

    const obs = this.modoEdicao && this.editandoId
      ? this.api.atualizarEvento(this.editandoId, payload as EventoAtualizar)
      : this.api.criarEvento(payload);

    obs.subscribe({
      next: () => {
        this.mostrarToast(this.modoEdicao ? 'Atualizada!' : 'Registrada!', 'success');
        this.fecharModal();
        this.notificarAtualizacaoDados();
        this.carregarDados();
      },
      error: e => this.mostrarToast(e.error?.detail || 'Erro ao salvar', 'error'),
    });
  }

  // ── Exclusão ───────────────────────────────────────────────────────────────

  pedirConfirmacao(id: number): void { this.confirmandoExclusao = id; }
  cancelarExclusao(): void { this.confirmandoExclusao = null; }

  confirmarExclusao(id: number): void {
    this.confirmandoExclusao = null;
    this.api.excluirEvento(id).subscribe({
      next: () => {
        this.mostrarToast('Excluída!', 'success');
        this.notificarAtualizacaoDados();
        this.carregarDados();
      },
      error: () => this.mostrarToast('Erro ao excluir', 'error'),
    });
  }

  // ── Histórico ──────────────────────────────────────────────────────────────

  abrirHistorico(): void { this.historicoModal.abrir(); }

  // ── Helpers ────────────────────────────────────────────────────────────────

  formatarDateTime(ts: string): string {
    if (!ts) return '-';
    const d = new Date(ts);
    return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  exibir(v: number | null): string {
    if (v === null || v === undefined) return '—';
    return (v * 10).toFixed(1).replace('.0', '');
  }

  barWidth(v: number | null): string {
    return v !== null ? `${Math.round(v * 100)}%` : '0%';
  }

  dimensoesExtrasEntries(e: Evento): Array<[string, number]> {
    return e.dimensoes_extras ? Object.entries(e.dimensoes_extras) : [];
  }

  formDimensoesExtrasEntries(): Array<[string, number]> {
    return Object.entries(this.form.dimensoesExtras);
  }

  contextoEntries(e: Evento): Array<[string, string]> {
    return e.contexto ? Object.entries(e.contexto) : [];
  }

  private formVazio(): FormEvento {
    return {
      evento: '', data_hora: this.agora(),
      energia: 5, humor: 5, estresse: 5, sensibilidade: 5, serenidade: 5, interesse: 5,
      descricao: '', tags: '',
      contextoChave: '', contextoValor: '', contextoItens: [],
      dimensoesExtrasNome: '', dimensoesExtrasValor: 5, dimensoesExtras: {},
    };
  }

  private agora(): string {
    const now = new Date();
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
    return now.toISOString().slice(0, 16);
  }

  private isoParaLocal(iso: string): string {
    if (!iso.includes('Z') && !iso.includes('+')) return iso.slice(0, 16);
    const d = new Date(iso);
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
  }

  mostrarToast(mensagem: string, tipo: string): void {
    this.toast = { mensagem, tipo };
    setTimeout(() => { this.toast = null; this.cdr.detectChanges(); }, 3500);
  }

  private notificarAtualizacaoDados(): void {
    const timestamp = String(Date.now());
    localStorage.setItem('diario_data_updated_at', timestamp);
    window.dispatchEvent(new CustomEvent('diario-data-updated', { detail: { timestamp } }));
  }
}
