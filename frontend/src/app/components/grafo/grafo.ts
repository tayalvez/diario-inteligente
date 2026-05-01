// src/app/components/grafo/grafo.ts
import {
  Component, OnInit, AfterViewInit, OnDestroy,
  ElementRef, ViewChild, ChangeDetectorRef
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from '../../services/api';
import { GrafoDados, GrafoNo, GrafoAresta } from '../../models/types';

declare const vis: any;

@Component({
  selector: 'app-grafo',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './grafo.html',
  styleUrl: './grafo.css',
})
export class GrafoComponent implements OnInit, AfterViewInit, OnDestroy {
  @ViewChild('grafoContainer') grafoContainer!: ElementRef;

  private network: any = null;
  private nodesDataset: any = null;
  private edgesDataset: any = null;

  grafoDados: GrafoDados | null = null;
  carregando = true;
  erro: string | null = null;
  modo: 'global' | 'local' = 'global';
  eventoCentralId: number | null = null;

  filtroDataInicio = '';
  filtroDataFim = '';
  profundidade = 2;

  painelAberto = false;
  noSelecionado: GrafoNo | null = null;
  arestasDoNo: GrafoAresta[] = [];
  private lastDataUpdateSeen = '';
  private readonly onDataUpdated = () => this.recarregarSeHouverMudanca();
  private readonly onStorageUpdated = (event: StorageEvent) => {
    if (event.key === 'diario_data_updated_at') this.recarregarSeHouverMudanca();
  };
  private readonly onVisibilityChanged = () => {
    if (!document.hidden) this.recarregarSeHouverMudanca();
  };

  private readonly graphPalette = {
    paper: '#F8F1E6',
    paperWarm: '#F3E7D4',
    ink: '#5C4B43',
    inkSoft: '#7A675D',
    edge: '#CFA18D',
    edgeText: '#8C6F63',
    edgeHighlight: '#B98573',
    selectedBorder: '#8D6E63',
    shadow: 'rgba(156, 124, 103, 0.22)',
  };

  constructor(
    private api: ApiService,
    private route: ActivatedRoute,
    private router: Router,
    private cdr: ChangeDetectorRef,
  ) {}

  ngOnInit(): void {
    this.lastDataUpdateSeen = localStorage.getItem('diario_data_updated_at') || '';
    window.addEventListener('diario-data-updated', this.onDataUpdated);
    window.addEventListener('storage', this.onStorageUpdated);
    window.addEventListener('focus', this.onDataUpdated);
    document.addEventListener('visibilitychange', this.onVisibilityChanged);

    this.route.queryParams.subscribe(params => {
      if (params['evento']) {
        this.eventoCentralId = Number(params['evento']);
        this.modo = 'local';
      } else {
        this.modo = 'global';
        this.eventoCentralId = null;
      }
      if (this.grafoContainer) this.carregarGrafo();
    });
  }

  ngAfterViewInit(): void { this.carregarGrafo(); }

  ngOnDestroy(): void {
    window.removeEventListener('diario-data-updated', this.onDataUpdated);
    window.removeEventListener('storage', this.onStorageUpdated);
    window.removeEventListener('focus', this.onDataUpdated);
    document.removeEventListener('visibilitychange', this.onVisibilityChanged);
    if (this.network) { this.network.destroy(); this.network = null; }
  }

  carregarGrafo(): void {
    if (!this.grafoContainer) return;
    this.carregando = true;
    this.erro = null;
    this.painelAberto = false;

    const obs = this.modo === 'local' && this.eventoCentralId
      ? this.api.grafoLocal(this.eventoCentralId, this.profundidade)
      : this.api.grafoGlobal({
          data_inicio: this.filtroDataInicio || undefined,
          data_fim: this.filtroDataFim || undefined,
        });

    obs.subscribe({
      next: (dados) => {
        this.grafoDados = dados;
        this.carregando = false;
        this.cdr.detectChanges();
        setTimeout(() => this.inicializarVis(dados), 50);
      },
      error: (e) => {
        this.erro = e.error?.detail || 'Erro ao carregar grafo';
        this.carregando = false;
        this.cdr.detectChanges();
      }
    });
  }

  private inicializarVis(dados: GrafoDados): void {
    if (!this.grafoContainer?.nativeElement || typeof vis === 'undefined') return;
    const container = this.grafoContainer.nativeElement;

    const nodes = dados.nodes.map(n => ({
      id: n.id, label: n.label, group: n.group, title: n.title,
      color: {
        background: n.color,
        border: this.darken(n.color),
        highlight: { background: this.lighten(n.color, 0.06), border: this.graphPalette.selectedBorder },
        hover: { background: this.lighten(n.color, 0.03), border: this.graphPalette.selectedBorder },
      },
      size: n.size || 16,
      font: { color: this.graphPalette.ink, size: 13, face: 'Nunito', bold: { color: this.graphPalette.ink } },
      chosen: false,
    }));

    const edges = dados.edges.map((e: GrafoAresta) => ({
      id: e.id, from: e.from, to: e.to, label: e.label,
      title: `Intensidade: ${Math.round(e.intensidade * 100)}% · Confiabilidade: ${Math.round(e.confiabilidade * 100)}%`,
      color: {
        color: this.graphPalette.edge,
        opacity: e.color?.opacity ?? 0.72,
        highlight: this.graphPalette.edgeHighlight,
        hover: this.graphPalette.edgeHighlight,
        inherit: false,
      },
      width: (e.width || 2) + 0.4,
      dashes: e.dashes || false,
      arrows: { to: { enabled: true, scaleFactor: 0.45, type: 'arrow' } },
      font: {
        size: 10,
        color: this.graphPalette.edgeText,
        face: 'Nunito',
        align: 'middle',
        strokeWidth: 3,
        strokeColor: this.graphPalette.paper,
      },
      smooth: { type: 'cubicBezier', roundness: 0.18 },
      selectionWidth: 1.2,
      hoverWidth: 0.6,
      chosen: false,
    }));

    if (this.network) {
      this.nodesDataset.clear(); this.edgesDataset.clear();
      this.nodesDataset.add(nodes); this.edgesDataset.add(edges);
      this.network.fit({ animation: { duration: 800, easingFunction: 'easeInOutQuad' } });
      return;
    }

    this.nodesDataset = new vis.DataSet(nodes);
    this.edgesDataset = new vis.DataSet(edges);

    this.network = new vis.Network(
      container,
      { nodes: this.nodesDataset, edges: this.edgesDataset },
      {
        physics: {
          forceAtlas2Based: { gravitationalConstant: -30, centralGravity: 0.008, springLength: 200, springConstant: 0.15 },
          maxVelocity: 120, solver: 'forceAtlas2Based', timestep: 0.35,
          stabilization: { iterations: 150 },
        },
        interaction: { hover: true, tooltipDelay: 150, navigationButtons: true, keyboard: { enabled: true } },
        nodes: {
          shape: 'dot',
          borderWidth: 2.5,
          borderWidthSelected: 3,
          shadow: { enabled: true, size: 14, x: 0, y: 6, color: this.graphPalette.shadow },
          margin: 10,
        },
        edges: {
          smooth: { type: 'cubicBezier', roundness: 0.18 },
          shadow: { enabled: false },
        },
        layout: { improvedLayout: nodes.length < 100 },
      }
    );

    this.network.on('click', (params: any) => {
      if (params.nodes.length > 0) this.onNodoClicado(params.nodes[0]);
      else if (params.edges.length === 0) this.fecharPainel();
    });
    this.network.on('stabilizationIterationsDone', () => {
      this.network.setOptions({ physics: { enabled: false } });
    });
  }

  onNodoClicado(nodeId: number): void {
    if (!this.grafoDados) return;
    this.noSelecionado = this.grafoDados.nodes.find(n => n.id === nodeId) || null;
    this.arestasDoNo = this.grafoDados.edges.filter(e => e.from === nodeId || e.to === nodeId);
    this.painelAberto = true;
    this.cdr.detectChanges();
  }

  fecharPainel(): void { this.painelAberto = false; this.cdr.detectChanges(); }
  verGrafoLocal(): void { if (this.noSelecionado) this.router.navigate(['/grafo'], { queryParams: { evento: this.noSelecionado.id } }); }
  verGlobal(): void { this.router.navigate(['/grafo']); }
  irParaEventos(): void { this.router.navigate(['/eventos']); }
  aplicarFiltros(): void { this.carregarGrafo(); }
  fitGrafo(): void { if (this.network) this.network.fit({ animation: { duration: 600, easingFunction: 'easeInOutQuad' } }); }

  private recarregarSeHouverMudanca(): void {
    const current = localStorage.getItem('diario_data_updated_at') || '';
    if (!current || current === this.lastDataUpdateSeen) return;
    this.lastDataUpdateSeen = current;
    this.carregarGrafo();
  }

  private darken(hex: string): string {
    if (!hex || hex.length < 7) return hex;
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    return `rgb(${Math.round(r * 0.75)},${Math.round(g * 0.75)},${Math.round(b * 0.75)})`;
  }

  private lighten(hex: string, amount: number): string {
    if (!hex || hex.length < 7) return hex;
    const r = parseInt(hex.slice(1, 3), 16);
    const g = parseInt(hex.slice(3, 5), 16);
    const b = parseInt(hex.slice(5, 7), 16);
    const mix = (channel: number) => Math.round(channel + (255 - channel) * amount);
    return `rgb(${mix(r)},${mix(g)},${mix(b)})`;
  }

  formatarData(ts: string): string {
    if (!ts) return '-';
    const d = new Date(ts.includes('Z') || ts.includes('+') ? ts : ts + 'Z');
    return d.toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  percentual(v: number): string { return `${Math.round((v || 0) * 100)}%`; }

  outroEvento(aresta: GrafoAresta): GrafoNo | null {
    if (!this.grafoDados || !this.noSelecionado) return null;
    const outroId = aresta.from === this.noSelecionado.id ? aresta.to : aresta.from;
    return this.grafoDados.nodes.find(n => n.id === outroId) || null;
  }

  motivoPartes(motivo: string | null): string[] {
    if (!motivo) return [];
    return motivo.split(';').map(p => p.trim()).filter(Boolean);
  }
}
