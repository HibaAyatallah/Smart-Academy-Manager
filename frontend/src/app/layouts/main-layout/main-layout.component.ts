import { AsyncPipe, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { BreakpointObserver } from '@angular/cdk/layout';
import { MatButtonModule } from '@angular/material/button';
import { MatSidenavModule } from '@angular/material/sidenav';
import { MatToolbarModule } from '@angular/material/toolbar';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { map, shareReplay } from 'rxjs/operators';

import { UserProfile } from '../../core/models/auth.models';
import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-main-layout',
  standalone: true,
  imports: [
    AsyncPipe,
    MatButtonModule,
    MatSidenavModule,
    MatToolbarModule,
    NgIf,
    RouterLink,
    RouterLinkActive,
    RouterOutlet,
  ],
  templateUrl: './main-layout.component.html',
  styleUrl: './main-layout.component.scss',
})
export class MainLayoutComponent {
  private readonly authService = inject(AuthService);
  private readonly breakpointObserver = inject(BreakpointObserver);

  readonly user$ = this.authService.currentUser$;
  readonly isCompact$ = this.breakpointObserver.observe('(max-width: 900px)').pipe(
    map((state) => state.matches),
    shareReplay(1),
  );

  dashboardLink(): string {
    const user = this.authService.currentUserSnapshot;
    return user ? this.authService.getDashboardUrlForRole(user.role) : '/dashboard';
  }

  canManageApplications(user: UserProfile): boolean {
    return user.role === 'SUPER_ADMIN' || user.role === 'HR';
  }

  canManageBusinessUnits(user: UserProfile): boolean {
    return user.role === 'SUPER_ADMIN' || user.role === 'HR' || user.role === 'BU_MANAGER';
  }

  canViewOwnApplications(user: UserProfile): boolean {
    return user.role === 'CANDIDATE';
  }

  logout(): void {
    this.authService.logout();
  }
}
