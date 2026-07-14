import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { PaginatedResponse } from '../models/application.models';
import { BusinessUnit, BusinessUnitMembership, BusinessUnitNeed } from '../models/business-unit.models';

@Injectable({
  providedIn: 'root'
})
export class BusinessUnitService {
  private readonly baseUrl = environment.apiBaseUrl;

  constructor(private http: HttpClient) {}

  // Business Units
  getBusinessUnits(params?: any): Observable<PaginatedResponse<BusinessUnit>> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get<PaginatedResponse<BusinessUnit>>(`${this.baseUrl}business-units/`, { params: httpParams });
  }

  getBusinessUnit(id: number): Observable<BusinessUnit> {
    return this.http.get<BusinessUnit>(`${this.baseUrl}business-units/${id}/`);
  }

  createBusinessUnit(data: Partial<BusinessUnit>): Observable<BusinessUnit> {
    return this.http.post<BusinessUnit>(`${this.baseUrl}business-units/`, data);
  }

  updateBusinessUnit(id: number, data: Partial<BusinessUnit>): Observable<BusinessUnit> {
    return this.http.patch<BusinessUnit>(`${this.baseUrl}business-units/${id}/`, data);
  }

  deleteBusinessUnit(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}business-units/${id}/`);
  }

  // Memberships
  getMemberships(params?: any): Observable<PaginatedResponse<BusinessUnitMembership>> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get<PaginatedResponse<BusinessUnitMembership>>(`${this.baseUrl}business-unit-memberships/`, { params: httpParams });
  }

  createMembership(data: Partial<BusinessUnitMembership>): Observable<BusinessUnitMembership> {
    return this.http.post<BusinessUnitMembership>(`${this.baseUrl}business-unit-memberships/`, data);
  }

  updateMembership(id: number, data: Partial<BusinessUnitMembership>): Observable<BusinessUnitMembership> {
    return this.http.patch<BusinessUnitMembership>(`${this.baseUrl}business-unit-memberships/${id}/`, data);
  }

  deleteMembership(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}business-unit-memberships/${id}/`);
  }

  // Needs
  getNeeds(params?: any): Observable<PaginatedResponse<BusinessUnitNeed>> {
    let httpParams = new HttpParams();
    if (params) {
      Object.keys(params).forEach(key => {
        if (params[key] !== null && params[key] !== undefined && params[key] !== '') {
          httpParams = httpParams.set(key, params[key]);
        }
      });
    }
    return this.http.get<PaginatedResponse<BusinessUnitNeed>>(`${this.baseUrl}business-unit-needs/`, { params: httpParams });
  }

  getNeed(id: number): Observable<BusinessUnitNeed> {
    return this.http.get<BusinessUnitNeed>(`${this.baseUrl}business-unit-needs/${id}/`);
  }

  createNeed(data: Partial<BusinessUnitNeed>): Observable<BusinessUnitNeed> {
    return this.http.post<BusinessUnitNeed>(`${this.baseUrl}business-unit-needs/`, data);
  }

  updateNeed(id: number, data: Partial<BusinessUnitNeed>): Observable<BusinessUnitNeed> {
    return this.http.patch<BusinessUnitNeed>(`${this.baseUrl}business-unit-needs/${id}/`, data);
  }

  deleteNeed(id: number): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}business-unit-needs/${id}/`);
  }
}
