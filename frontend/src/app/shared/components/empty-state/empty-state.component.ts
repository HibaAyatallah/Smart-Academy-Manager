import { Component, Input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-empty-state',
  standalone: true,
  imports: [MatIconModule],
  template: `
    <section class="empty" role="status">
      <mat-icon aria-hidden="true">{{ icon }}</mat-icon>
      <h2>{{ title }}</h2>
      <p>{{ message }}</p>
      <ng-content />
    </section>
  `,
  styles: [`
    .empty { display: grid; min-height: 220px; place-items: center; align-content: center; gap: 9px; padding: clamp(24px, 4vw, 40px); border: 1px dashed #cbd5e1; border-radius: 18px; background: radial-gradient(circle at 50% 0,rgba(99,102,241,.07),transparent 55%),linear-gradient(145deg,#fff,#f8faff); color: var(--app-text-muted); text-align: center; }
    mat-icon { display: grid; width: 56px; height: 56px; margin-bottom: 4px; place-items: center; border-radius: 17px; background: #eef2ff; color: #4f46e5; font-size: 28px; box-shadow: 0 8px 20px rgba(79,70,229,.12); }
    h2 { margin: 4px 0 0; color: var(--app-text); font-size: 1rem; font-weight: 720; }
    p { max-width: 520px; margin: 0; font-size: .86rem; line-height: 1.5; }
  `],
})
export class EmptyStateComponent {
  @Input() icon = 'inbox';
  @Input({ required: true }) title = '';
  @Input() message = '';
  @Input() set description(value: string) { this.message = value; }
}
