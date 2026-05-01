// src/app/app.routes.ts
import { Routes } from '@angular/router';
import { DashboardComponent } from './components/dashboard/dashboard';
import { ExperienciasComponent } from './components/experiencias/experiencias';
import { InsightsComponent } from './components/insights/insights';
import { GrafoComponent } from './components/grafo/grafo';

export const routes: Routes = [
  { path: '',           redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard',  component: DashboardComponent },
  { path: 'eventos',    component: ExperienciasComponent },
  { path: 'grafo',      component: GrafoComponent },
  { path: 'insights',   component: InsightsComponent },
  { path: '**',         redirectTo: 'dashboard' },
];
