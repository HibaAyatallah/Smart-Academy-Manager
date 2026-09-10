import { DatePipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';

import { EDUCATION_LEVEL_LABELS } from '../../../core/models/application.models';
import { Offer } from '../../../core/models/offer.models';
import { OfferService } from '../../../core/services/offer.service';
import { isOfferOpen, mainSkills } from './public-offers.utils';

@Component({
  selector: 'app-public-offer-detail', standalone: true,
  imports: [DatePipe, NgFor, NgIf, MatProgressSpinnerModule, RouterLink],
  templateUrl: './public-offer-detail.component.html', styleUrl: './public-offers.component.scss',
})
export class PublicOfferDetailComponent {
  private readonly offerService = inject(OfferService);
  private readonly route = inject(ActivatedRoute);
  offer: Offer | null = null;
  isLoading = true;
  hasError = false;

  constructor() {
    const id = Number(this.route.snapshot.paramMap.get('id'));
    if (!Number.isSafeInteger(id) || id <= 0) { this.isLoading = false; this.hasError = true; return; }
    this.offerService.getOffer(id).pipe(finalize(() => this.isLoading = false)).subscribe({
      next: offer => this.offer = isOfferOpen(offer) ? offer : null,
      error: () => this.hasError = true,
    });
  }

  skills(offer: Offer): string[] { return mainSkills(offer); }
  level(offer: Offer): string { return offer.required_level ? EDUCATION_LEVEL_LABELS[offer.required_level] : 'Non précisé'; }
}
