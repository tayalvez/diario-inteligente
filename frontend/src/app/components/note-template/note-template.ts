import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TemplateType } from '../../services/template.service';

@Component({
  selector: 'app-note-template',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './note-template.html',
  styleUrl: './note-template.css',
})
export class NoteTemplateComponent {
  @Input() template: TemplateType = 'kawaii';

  get cls(): string { return `nt nt-${this.template}`; }
}
