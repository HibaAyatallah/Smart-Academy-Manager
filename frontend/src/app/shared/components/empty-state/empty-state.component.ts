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
    </section>
  `,
  styles: [`
    .empty { display: grid; min-height: 220px; place-items: center; align-content: center; gap: 8px; padding: 32px; border: 1px dashed var(--app-border); border-radius: var(--app-radius-lg); background: var(--app-surface); color: var(--app-text-muted); text-align: center; }
    mat-icon { width: 36px; height: 36px; color: var(--app-primary); font-size: 36px; }
    h2 { margin: 4px 0 0; color: var(--app-text); font-size: 1rem; }
    p { max-width: 520px; margin: 0; font-size: .86rem; line-height: 1.5; }
  `],
})
export class EmptyStateComponent {
  @Input() icon = 'inbox';
  @Input({ required: true }) title = '';
  @Input({ required: true }) message = '';
}
