import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { environment } from '../../../environments/environment';
import { ContactService } from './contact.service';

describe('ContactService', () => {
  let service: ContactService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(ContactService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('submits a contact message to the public API', () => {
    const payload = {
      full_name: 'Ahmed Benjelloun', email: 'ahmed@example.com', request_type: 'Formation',
      subject: 'Demande de formation', message: 'Je souhaite obtenir davantage d’informations.',
    };
    service.submit(payload).subscribe();
    const request = http.expectOne(`${environment.apiBaseUrl}contact-messages/`);
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(payload);
    request.flush({ id: 1, status: 'NEW', created_at: new Date().toISOString(), ...payload });
  });
});
