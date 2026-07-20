import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';

import { finalize, switchMap } from 'rxjs/operators';
import { APPLICATION_TYPE_LABELS, EDUCATION_LEVEL_LABELS } from '../../../core/models/application.models';
import { OFFER_STATUS_LABELS, Offer } from '../../../core/models/offer.models';
import { AuthService } from '../../../core/services/auth.service';
import { OfferService } from '../../../core/services/offer.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-offer-detail',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatDividerModule,
    MatChipsModule,
    MatProgressSpinnerModule,
    MatSnackBarModule,
    PageHeaderComponent,
  ],
  templateUrl: './offer-detail.component.html',
  styleUrls: ['./offer-detail.component.scss'],
})
export class OfferDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly offerService = inject(OfferService);
  private readonly authService = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);

  offer: Offer | null = null;
  isLoading = true;
  errorMessage = '';

  get isCandidate(): boolean {
    return this.authService.currentUserSnapshot?.role === 'CANDIDATE';
  }

  get isSuperAdmin(): boolean {
    return this.authService.currentUserSnapshot?.role === 'SUPER_ADMIN';
  }

  ngOnInit(): void {
    this.route.paramMap
      .pipe(
        switchMap((params) => {
          this.isLoading = true;
          this.errorMessage = '';
          const id = Number(params.get('id'));
          return this.offerService.getOffer(id);
        }),
        finalize(() => (this.isLoading = false)),
      )
      .subscribe({
        next: (offer) => {
          this.offer = offer;
        },
        error: () => {
          this.errorMessage = 'Impossible de charger l\'offre. Elle a peut-être été supprimée ou n\'est plus disponible.';
        },
      });
  }

  publish(): void {
    if (!this.offer) return;
    this.offerService.publishOffer(this.offer.id).subscribe({
      next: (updated) => {
        this.offer = updated;
        this.snackBar.open('Offre publiée avec succès.', 'Fermer', { duration: 3000 });
      },
      error: () => this.snackBar.open('Erreur lors de la publication.', 'Fermer', { duration: 3000 }),
    });
  }

  closeOffer(): void {
    if (!this.offer) return;
    this.offerService.closeOffer(this.offer.id).subscribe({
      next: (updated) => {
        this.offer = updated;
        this.snackBar.open('Offre fermée avec succès.', 'Fermer', { duration: 3000 });
      },
      error: () => this.snackBar.open('Erreur lors de la fermeture.', 'Fermer', { duration: 3000 }),
    });
  }

  archive(): void {
    if (!this.offer) return;
    this.offerService.archiveOffer(this.offer.id).subscribe({
      next: (updated) => {
        this.offer = updated;
        this.snackBar.open('Offre archivée avec succès.', 'Fermer', { duration: 3000 });
      },
      error: () => this.snackBar.open('Erreur lors de l\'archivage.', 'Fermer', { duration: 3000 }),
    });
  }

  deleteOffer(): void {
    if (!this.offer || !confirm('Êtes-vous sûr de vouloir supprimer cette offre ?')) return;
    this.offerService.deleteOffer(this.offer.id).subscribe({
      next: () => {
        this.snackBar.open('Offre supprimée.', 'Fermer', { duration: 3000 });
        this.router.navigate(['/offers']);
      },
      error: () => this.snackBar.open('Erreur lors de la suppression.', 'Fermer', { duration: 3000 }),
    });
  }

  typeLabel(type: any): string {
    return APPLICATION_TYPE_LABELS[type as keyof typeof APPLICATION_TYPE_LABELS] || type;
  }

  statusLabel(status: any): string {
    return OFFER_STATUS_LABELS[status as keyof typeof OFFER_STATUS_LABELS] || status;
  }

  levelLabel(level: any): string {
    if (!level) return 'Non spécifié';
    return EDUCATION_LEVEL_LABELS[level as keyof typeof EDUCATION_LEVEL_LABELS] || level;
  }
}
