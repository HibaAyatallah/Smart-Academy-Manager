import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { PaginatedResponse } from '../models/application.models';
import { UserProfile, UserRole } from '../models/auth.models';

export interface UserPayload {
  email: string;
  password?: string;
  first_name: string;
  last_name: string;
  phone_number: string;
  role: UserRole;
  is_active: boolean;
  business_unit_id?: number | null;
}

@Injectable({ providedIn: 'root' })
export class UserManagementService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiBaseUrl}users/`;

  getUsers(params: Record<string, unknown> = {}): Observable<PaginatedResponse<UserProfile>> {
    let httpParams = new HttpParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') httpParams = httpParams.set(key, String(value));
    });
    return this.http.get<PaginatedResponse<UserProfile>>(this.baseUrl, { params: httpParams });
  }

  getUser(id: number): Observable<UserProfile> {
    return this.http.get<UserProfile>(`${this.baseUrl}${id}/`);
  }

  createUser(payload: UserPayload): Observable<UserProfile> {
    return this.http.post<UserProfile>(this.baseUrl, payload);
  }

  updateUser(id: number, payload: Partial<UserPayload>): Observable<UserProfile> {
    return this.http.patch<UserProfile>(`${this.baseUrl}${id}/`, payload);
  }
}
