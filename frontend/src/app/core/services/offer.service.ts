import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { PaginatedResponse } from '../models/application.models';
import { Offer, OfferCreateUpdate, OfferStatus } from '../models/offer.models';

export interface OfferFilters {
  status?: OfferStatus | '';
  business_unit?: number | '';
  search?: string;
  page?: number;
}

@Injectable({
  providedIn: 'root',
})
export class OfferService {
  private http = inject(HttpClient);
  private apiUrl = `${environment.apiBaseUrl}offers/`;

  getOffers(filters?: OfferFilters): Observable<PaginatedResponse<Offer>> {
    let params = new HttpParams();
    if (filters) {
      if (filters.status) params = params.set('status', filters.status);
      if (filters.business_unit) params = params.set('business_unit', filters.business_unit.toString());
      if (filters.search) params = params.set('search', filters.search);
      if (filters.page) params = params.set('page', filters.page.toString());
    }
    return this.http.get<PaginatedResponse<Offer>>(this.apiUrl, { params });
  }

  getOffer(id: number): Observable<Offer> {
    return this.http.get<Offer>(`${this.apiUrl}${id}/`);
  }

  createOffer(data: OfferCreateUpdate): Observable<Offer> {
    return this.http.post<Offer>(this.apiUrl, data);
  }

  updateOffer(id: number, data: Partial<OfferCreateUpdate>): Observable<Offer> {
    return this.http.patch<Offer>(`${this.apiUrl}${id}/`, data);
  }

  deleteOffer(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}${id}/`);
  }

  publishOffer(id: number): Observable<Offer> {
    return this.http.post<Offer>(`${this.apiUrl}${id}/publish/`, {});
  }

  closeOffer(id: number): Observable<Offer> {
    return this.http.post<Offer>(`${this.apiUrl}${id}/close/`, {});
  }

  archiveOffer(id: number): Observable<Offer> {
    return this.http.post<Offer>(`${this.apiUrl}${id}/archive/`, {});
  }
}
