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
  it('records and validates session attendance', () => {
    service.recordAttendance(12, 'PRESENT', 'On time').subscribe();
    const record = http.expectOne(`${environment.apiBaseUrl}attendance/`);
    expect(record.request.body).toEqual({ enrollment: 12, status: 'PRESENT', note: 'On time' });
    record.flush({});
    service.validateAttendance(3).subscribe();
    const validate = http.expectOne(`${environment.apiBaseUrl}attendance/3/validate/`);
    expect(validate.request.method).toBe('POST');
    validate.flush({});
  });
  it('downloads certificates through the protected endpoint', () => {
    service.downloadCertificate(7).subscribe();
    const request = http.expectOne(`${environment.apiBaseUrl}certificates/7/download/`);
    expect(request.request.responseType).toBe('blob');
    request.flush(new Blob());
  });
});
