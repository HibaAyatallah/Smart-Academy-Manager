import { Component, OnInit, inject } from '@angular/core';
import { Router } from '@angular/router';
import { take } from 'rxjs/operators';

import { AuthService } from '../../core/services/auth.service';

@Component({
  selector: 'app-dashboard-redirect',
  standalone: true,
  template: '',
})
export class DashboardRedirectComponent implements OnInit {
  private readonly authService = inject(AuthService);
  private readonly router = inject(Router);

  ngOnInit(): void {
    this.authService
      .ensureProfile()
      .pipe(take(1))
      .subscribe({
        next: (profile) => {
          const dashboardUrl = this.authService.getDashboardUrlForRole(profile.role);
          void this.router.navigateByUrl(dashboardUrl);
        },
        error: () => {
          console.error('[Auth] Profil indisponible pour la redirection.');
          this.authService.logout();
        },
      });
  }
}
