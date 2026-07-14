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
        status: 'SUBMITTED',
        page: 2,
      })
      .subscribe();

    const request = httpController.expectOne(
      (request) => request.url === '/api/applications/',
    );
    expect(request.request.params.get('search')).toBe('Jane Candidate');
    expect(request.request.params.get('application_type')).toBe('PFA_INTERNSHIP');
    expect(request.request.params.get('status')).toBe('SUBMITTED');
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
});
