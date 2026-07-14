import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';

import { environment } from '../../../environments/environment';
import {
  Application,
  ApplicationFilters,
  PaginatedResponse,
} from '../models/application.models';

export interface ApplicationApiError {
  status: number;
  message: string;
  raw: unknown;
}

@Injectable({
  providedIn: 'root',
})
export class ApplicationService {
  private readonly http = inject(HttpClient);
  private readonly apiBaseUrl = environment.apiBaseUrl;

  submitPublicApplication(formData: FormData): Observable<Application> {
    return this.http.post<Application>(`${this.apiBaseUrl}applications/public-submit/`, formData);
  }

  getMyApplications(page = 1): Observable<PaginatedResponse<Application>> {
    const url = `${this.apiBaseUrl}applications/mine/`;
    let params = new HttpParams();
    if (page > 1) {
      params = params.set('page', page);
    }
    return this.http
      .get<PaginatedResponse<Application> | Application[]>(url, {
        observe: 'response',
        params,
      })
      .pipe(
        map((response) => this.normalizePaginatedResponse(response.body)),
        catchError((error: HttpErrorResponse) => {
          return throwError(() => this.toApplicationApiError(error));
        }),
      );
  }

  listApplications(filters: ApplicationFilters): Observable<PaginatedResponse<Application>> {
    let params = new HttpParams();
    if (filters.application_type) {
      params = params.set('application_type', filters.application_type);
    }
    if (filters.status) {
      params = params.set('status', filters.status);
    }
    if (filters.search?.trim()) {
      params = params.set('search', filters.search.trim());
    }
    if (filters.page && filters.page > 1) {
      params = params.set('page', filters.page);
    }
    const url = `${this.apiBaseUrl}applications/`;
    return this.http
      .get<PaginatedResponse<Application> | Application[]>(url, {
        observe: 'response',
        params,
      })
      .pipe(
        map((response) => this.normalizePaginatedResponse(response.body)),
        catchError((error: HttpErrorResponse) => {
          return throwError(() => this.toApplicationApiError(error));
        }),
      );
  }

  getApplication(id: number): Observable<Application> {
    return this.http.get<Application>(`${this.apiBaseUrl}applications/${id}/`);
  }

  downloadDocument(downloadUrl: string): Observable<Blob> {
    return this.http.get(downloadUrl, {
      responseType: 'blob',
    });
  }

  private normalizePaginatedResponse(
    response: PaginatedResponse<Application> | Application[] | null,
  ): PaginatedResponse<Application> {
    if (Array.isArray(response)) {
      return {
        count: response.length,
        next: null,
        previous: null,
        results: response,
      };
    }
    return (
      response ?? {
        count: 0,
        next: null,
        previous: null,
        results: [],
      }
    );
  }

  private toApplicationApiError(error: HttpErrorResponse): ApplicationApiError {
    const detail =
      typeof error.error === 'object' &&
      error.error !== null &&
      'detail' in error.error &&
      typeof error.error.detail === 'string'
        ? error.error.detail
        : null;

    return {
      status: error.status || 0,
      message: detail ?? error.message ?? 'Erreur API applications.',
      raw: error,
    };
  }

  markUnderReview(id: number): Observable<Application> {
    return this.http.post<Application>(`${this.apiBaseUrl}applications/${id}/mark-under-review/`, {});
  }

  preselect(id: number): Observable<Application> {
    return this.http.post<Application>(`${this.apiBaseUrl}applications/${id}/preselect/`, {});
  }

  scheduleInterview(
    id: number,
    payload: {
      scheduled_at: string;
      location?: string;
      meeting_link?: string;
      notes?: string;
    },
  ): Observable<Application> {
    return this.http.post<Application>(
      `${this.apiBaseUrl}applications/${id}/schedule-interview/`,
      payload,
    );
  }

  completeInterview(id: number): Observable<Application> {
    return this.http.post<Application>(`${this.apiBaseUrl}applications/${id}/complete-interview/`, {});
  }

  accept(id: number): Observable<Application> {
    return this.http.post<Application>(`${this.apiBaseUrl}applications/${id}/accept/`, {});
  }

  reject(id: number, reason: string): Observable<Application> {
    return this.http.post<Application>(`${this.apiBaseUrl}applications/${id}/reject/`, {
      reason,
    });
  }
}
