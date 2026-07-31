import { AsyncPipe, NgFor, NgIf } from '@angular/common';
import { BreakpointObserver } from '@angular/cdk/layout';
import { Component, DestroyRef, ViewChild, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatSidenav, MatSidenavModule } from '@angular/material/sidenav';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { map, shareReplay } from 'rxjs/operators';

import { navigationForRole } from '../../core/navigation/authenticated-navigation';
import { ROLE_LABELS, UserProfile } from '../../core/models/auth.models';
import { AuthService } from '../../core/services/auth.service';
import { LanguageService } from '../../core/i18n/language.service';
import { AppLanguage } from '../../core/i18n/translations';
import { TranslatePipe } from '../../core/i18n/translate.pipe';
import { ChatbotComponent } from '../../shared/components/chatbot/chatbot.component';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [
    AsyncPipe,
    MatButtonModule,
    MatDividerModule,
    MatIconModule,
    MatMenuModule,
    MatSidenavModule,
    MatSelectModule,
    MatTooltipModule,
    NgFor,
    NgIf,
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
    TranslatePipe,
    ChatbotComponent,
  ],
  templateUrl: './main-layout.component.html',
  styleUrl: './main-layout.component.scss',
})
export class MainLayoutComponent {
  @ViewChild('drawer') drawer?: MatSidenav;

  private readonly authService = inject(AuthService);
  readonly language = inject(LanguageService);
  private readonly breakpointObserver = inject(BreakpointObserver);
  private readonly destroyRef = inject(DestroyRef);

  readonly roleLabels = ROLE_LABELS;
  readonly viewModel$ = this.authService.ensureProfile().pipe(
    map((user) => { this.language.initializeFromProfile(user.preferred_language); return ({user,navigation:navigationForRole(user.role)}); }),
    shareReplay({ bufferSize: 1, refCount: true }),
  );
  readonly isHandset$ = this.breakpointObserver.observe('(max-width: 767px)').pipe(
    map((state) => state.matches),
    shareReplay({ bufferSize: 1, refCount: true }),
  );
  private isHandset = false;
  sidebarCollapsed = false;

  constructor() {
    this.isHandset$
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value) => this.isHandset = value);
  }

  toggleNavigation(): void {
    if (this.isHandset) {
      void this.drawer?.toggle();
      return;
    }
    this.sidebarCollapsed = !this.sidebarCollapsed;
  }

  closeMobileNavigation(): void {
    if (this.isHandset) {
      void this.drawer?.close();
    }
  }

  initials(user: UserProfile): string {
    const parts = (user.full_name ?? '').trim().split(/\s+/).filter(Boolean);
    if (!parts.length) return (user.email ?? '').slice(0, 2).toUpperCase();
    return `${parts[0][0] ?? ''}${parts.at(-1)?.[0] ?? ''}`.toUpperCase();
  }

  logout(): void {
    this.authService.logout();
  }
  setLanguage(value: AppLanguage): void { this.language.setLanguage(value); this.authService.updateLanguage(value).subscribe({error:()=>void 0}); }
}
