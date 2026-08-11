import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';

export interface ContactMessagePayload {
  full_name: string;
  email: string;
  request_type: string;
  subject: string;
  message: string;
}

export interface ContactMessageResponse extends ContactMessagePayload {
  id: number;
  status: 'NEW' | 'IN_PROGRESS' | 'RESOLVED';
  created_at: string;
}

@Injectable({ providedIn: 'root' })
export class ContactService {
  private readonly http = inject(HttpClient);

  submit(payload: ContactMessagePayload): Observable<ContactMessageResponse> {
    return this.http.post<ContactMessageResponse>(
      `${environment.apiBaseUrl}contact-messages/`,
      payload,
    );
  }
}
