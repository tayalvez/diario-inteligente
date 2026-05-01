import { Component, Input } from '@angular/core';

type PhosphorWeight = 'regular' | 'bold' | 'fill' | 'duotone' | 'light' | 'thin';

@Component({
  selector: 'app-ph-icon',
  standalone: true,
  template: `<i [class]="cssClasses" [style.font-size]="size + 'px'" [style.color]="color || null"></i>`,
})
export class PhIconComponent {
  @Input() name = 'DotsThree';
  @Input() weight: PhosphorWeight = 'regular';
  @Input() size: number | string = 20;
  @Input() color?: string;

  get cssClasses(): string {
    const weightClass = this.weight === 'regular' ? 'ph' : `ph-${this.weight}`;
    const iconClass = 'ph-' + this.toKebab(this.name);
    return `${weightClass} ${iconClass}`;
  }

  private toKebab(name: string): string {
    return name.charAt(0).toLowerCase() +
      name.slice(1).replace(/[A-Z]/g, c => '-' + c.toLowerCase());
  }
}
