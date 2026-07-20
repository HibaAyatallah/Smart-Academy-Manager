import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../environments/environment';
import { TrainingService } from './training.service';

describe('TrainingService', () => {
  let service: TrainingService;
  let http: HttpTestingController;
  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(TrainingService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());
  it('loads filtered trainings', () => {
    service.getTrainings({ status: 'PUBLISHED' }).subscribe();
    const req = http.expectOne(request => request.url === `${environment.apiBaseUrl}trainings/`);
    expect(req.request.params.get('status')).toBe('PUBLISHED');
    req.flush({ count: 0, next: null, previous: null, results: [] });
  });
  it('requests enrollment for the selected session', () => {
    service.requestEnrollment(4, 9).subscribe();
    const req = http.expectOne(`${environment.apiBaseUrl}enrollments/`);
    expect(req.request.body).toEqual({ training: 4, session: 9 });
    req.flush({});
  });
  it('posts manager approval decisions', () => {
    service.decideEnrollment(2, 'manager_approve', 'Validé').subscribe();
    const req = http.expectOne(`${environment.apiBaseUrl}enrollments/2/manager_approve/`);
    expect(req.request.body).toEqual({ approved: true, comment: 'Validé' });
    req.flush({});
  });
  it('loads the isolated client endpoint', () => {
    service.getClientTrainings().subscribe();
    http.expectOne(`${environment.apiBaseUrl}client/trainings/`).flush({ count: 0, next: null, previous: null, results: [] });
  });
});
