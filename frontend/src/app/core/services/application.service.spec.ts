import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';

import { Application } from '../models/application.models';
import { ApplicationService } from './application.service';

describe('ApplicationService', () => {
  let service: ApplicationService;
  let httpController: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(ApplicationService);
    httpController = TestBed.inject(HttpTestingController);
  });

  afterEach(() => httpController.verify());

  it('sends the DRF page and active filters when listing applications', () => {
    service
      .listApplications({
        search: 'Jane Candidate',
        application_type: 'PFA_INTERNSHIP',
        status: 'RECEIVED',
        page: 2,
      })
      .subscribe();

    const request = httpController.expectOne(
      (request) => request.url === '/api/applications/',
    );
    expect(request.request.params.get('search')).toBe('Jane Candidate');
    expect(request.request.params.get('application_type')).toBe('PFA_INTERNSHIP');
    expect(request.request.params.get('status')).toBe('RECEIVED');
    expect(request.request.params.get('page')).toBe('2');
    request.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('normalizes a legacy array response for the candidate list', () => {
    let response: Application[] = [];
    service.getMyApplications(2).subscribe((value) => {
      response = value.results;
      expect(value.count).toBe(1);
    });

    const request = httpController.expectOne(
      (request) => request.url === '/api/applications/mine/',
    );
    expect(request.request.params.get('page')).toBe('2');
    request.flush([{ id: 1 } as Application]);

    expect(response).toEqual([{ id: 1 } as Application]);
  });

  it('exposes a structured API error for paginated requests', () => {
    let errorMessage = '';
    service.getMyApplications().subscribe({
      error: (error) => {
        errorMessage = error.message;
        expect(error.status).toBe(403);
      },
    });

    const request = httpController.expectOne('/api/applications/mine/');
    request.flush({ detail: 'Accès refusé.' }, { status: 403, statusText: 'Forbidden' });

    expect(errorMessage).toBe('Accès refusé.');
  });

  it('posts an employee conversion with the backend contract', () => {
    service.convertApplication(7, {
      conversion_type: 'EMPLOYEE', business_unit: 3,
    }).subscribe();

    const request = httpController.expectOne('/api/applications/7/convert/');
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual({
      conversion_type: 'EMPLOYEE', business_unit: 3,
    });
    request.flush({
      detail: 'Candidat converti avec succès.', conversion_type: 'EMPLOYEE',
      profile_id: 9, login_email: 'candidate@example.com',
      credentials_preserved: true, application: { id: 7 } as Application,
    });
  });

  it('uses multipart when the internship specification is supplied', () => {
    const specification = new File(['%PDF-1.4'], 'specification.pdf', {
      type: 'application/pdf',
    });
    service.convertApplication(7, {
      conversion_type: 'INTERN', business_unit: 3, supervisor: 5,
      paid: true, specification_pdf: specification,
    }).subscribe();

    const request = httpController.expectOne('/api/applications/7/convert/');
    expect(request.request.body instanceof FormData).toBeTrue();
    expect(request.request.body.get('conversion_type')).toBe('INTERN');
    expect(request.request.body.get('business_unit')).toBe('3');
    expect(request.request.body.get('supervisor')).toBe('5');
    expect(request.request.body.get('specification_pdf')).toBe(specification);
    request.flush({
      detail: 'Candidat converti avec succès.', conversion_type: 'INTERN',
      profile_id: 10, login_email: 'candidate@example.com',
      credentials_preserved: true, application: { id: 7 } as Application,
    });
  });
});
