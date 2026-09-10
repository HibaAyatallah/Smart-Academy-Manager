import { DatePipe, NgFor, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { RouterLink } from '@angular/router';
import { EMPTY, expand, finalize, map, reduce } from 'rxjs';

import { EDUCATION_LEVEL_LABELS } from '../../../core/models/application.models';
import { Offer } from '../../../core/models/offer.models';
import { OfferService } from '../../../core/services/offer.service';
import { isOfferOpen, mainSkills } from './public-offers.utils';

@Component({
  selector: 'app-public-offer-list', standalone: true,
  imports: [DatePipe, NgFor, NgIf, MatIconModule, MatProgressSpinnerModule, RouterLink],
  templateUrl: './public-offer-list.component.html', styleUrl: './public-offers.component.scss',
})
export class PublicOfferListComponent {
  private readonly offerService = inject(OfferService);
  offers: Offer[] = [];
  isLoading = true;
  hasError = false;

  constructor() {
    this.offerService.getOffers({ status: 'PUBLISHED', page: 1 }).pipe(
      expand((response, index) => response.next ? this.offerService.getOffers({ status: 'PUBLISHED', page: index + 2 }) : EMPTY),
      map(response => response.results),
      reduce((all, page) => [...all, ...page], [] as Offer[]),
      map(offers => offers.filter(offer => isOfferOpen(offer))),
      finalize(() => this.isLoading = false),
    ).subscribe({ next: offers => this.offers = offers, error: () => this.hasError = true });
  }

  skills(offer: Offer): string[] { return mainSkills(offer); }
  level(offer: Offer): string { return offer.required_level ? EDUCATION_LEVEL_LABELS[offer.required_level] : 'Non précisé'; }
}
