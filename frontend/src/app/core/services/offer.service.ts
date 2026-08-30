import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { CandidateRankingRow, PaginatedResponse } from '../models/application.models';
import { Offer, OfferCreateUpdate, OfferStatus } from '../models/offer.models';

const OFFER_DATE_FIELDS = ['start_date', 'end_date', 'application_deadline'] as const;

export function serializeOfferDate(value: string | Date | null | undefined): string | null | undefined {
  if (value === null || value === undefined || value === '') return value || null;
  if (typeof value === 'string') {
    const trimmed = value.trim();
    const iso = /^(\d{4})-(\d{2})-(\d{2})(?:T.*)?$/.exec(trimmed);
    if (iso) return `${iso[1]}-${iso[2]}-${iso[3]}`;
    const locale = /^(\d{1,2})\/(\d{1,2})\/(\d{4})$/.exec(trimmed);
    if (locale) return `${locale[3]}-${locale[1].padStart(2, '0')}-${locale[2].padStart(2, '0')}`;
  }
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export function serializeOfferPayload(data: Partial<OfferCreateUpdate>): Partial<OfferCreateUpdate> {
  const payload = { ...data };
  for (const field of OFFER_DATE_FIELDS) {
    if (field in payload) payload[field] = serializeOfferDate(payload[field]);
  }
  return payload;
}

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
    return this.http.post<Offer>(this.apiUrl, serializeOfferPayload(data));
  }

  updateOffer(id: number, data: Partial<OfferCreateUpdate>): Observable<Offer> {
    return this.http.patch<Offer>(`${this.apiUrl}${id}/`, serializeOfferPayload(data));
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

  getCandidateRanking(id: number): Observable<{offer: Offer; ranking: CandidateRankingRow[]}> {
    return this.http.get<{offer: Offer; ranking: CandidateRankingRow[]}>(`${this.apiUrl}${id}/candidate-ranking/`);
  }
}
