import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

export type TemplateType = 'kawaii' | 'notebook' | 'grid' | 'clean';

export const TEMPLATES: Array<{ id: TemplateType; label: string; icon: string }> = [
  { id: 'kawaii',    label: 'Kawaii',     icon: '🌸' },
  { id: 'notebook',  label: 'Caderno',    icon: '📓' },
  { id: 'grid',      label: 'Grade',      icon: '⬜' },
  { id: 'clean',     label: 'Clean',      icon: '✦'  },
];

const KEY = 'noteTemplate';

@Injectable({ providedIn: 'root' })
export class TemplateService {
  private _current = new BehaviorSubject<TemplateType>(
    (localStorage.getItem(KEY) as TemplateType) || 'kawaii'
  );

  template$ = this._current.asObservable();
  get current(): TemplateType { return this._current.value; }

  set(t: TemplateType): void {
    this._current.next(t);
    localStorage.setItem(KEY, t);
  }
}
