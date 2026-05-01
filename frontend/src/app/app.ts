// src/app/app.ts
import { Component } from '@angular/core';
import { RouterOutlet, RouterLink, RouterLinkActive } from '@angular/router';
import { ApiService } from './services/api';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink, RouterLinkActive],
  templateUrl: './app.html',
  styleUrl: './app.css'
})
export class App {
  title = 'Diário Inteligente';
  streakAtual = 0;

  constructor(private api: ApiService) {
    this.api.streak().subscribe({
      next: (s) => this.streakAtual = s.streak_atual,
      error: () => {}
    });
  }
}
