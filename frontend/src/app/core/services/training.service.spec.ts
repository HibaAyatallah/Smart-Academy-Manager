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
  it('loads more than 20 filtered items by following next and removes page overlap', () => {
    let result: Array<{id: number}> = [];
    service.getAllTrainings({ status: 'PUBLISHED', search: 'angular' }).subscribe(items => result = items);

    const first = http.expectOne(request => request.url === `${environment.apiBaseUrl}trainings/`);
    expect(first.request.params.get('status')).toBe('PUBLISHED');
    expect(first.request.params.get('search')).toBe('angular');
    const firstPage = Array.from({length: 20}, (_, index) => ({id: index + 1}));
    const nextUrl = `${environment.apiBaseUrl}trainings/?page=2&search=angular&status=PUBLISHED`;
    first.flush({count: 25, next: nextUrl, previous: null, results: firstPage});

    const second = http.expectOne(nextUrl);
    second.flush({
      count: 25,
      next: null,
      previous: `${environment.apiBaseUrl}trainings/?page=1&search=angular&status=PUBLISHED`,
      results: [{id: 20}, ...Array.from({length: 5}, (_, index) => ({id: index + 21}))],
    });

    expect(result.map(item => item.id)).toEqual(Array.from({length: 25}, (_, index) => index + 1));
  });
  it('fails instead of looping when DRF returns an already visited next link', () => {
    let error: Error | undefined;
    service.getAllAttendance().subscribe({error: value => error = value});
    const request = http.expectOne(`${environment.apiBaseUrl}attendance/`);
    request.flush({count: 21, next: `${environment.apiBaseUrl}attendance/`, previous: null, results: []});
    expect(error?.message).toContain('cyclique');
  });
  it('propagates an API error from a later page', () => {
    let failed = false;
    service.getAllEnrollments({session: 9}).subscribe({error: () => failed = true});
    const first = http.expectOne(request => request.url === `${environment.apiBaseUrl}enrollments/`);
    expect(first.request.params.get('session')).toBe('9');
    const nextUrl = `${environment.apiBaseUrl}enrollments/?page=2&session=9`;
    first.flush({count: 21, next: nextUrl, previous: null, results: [{id: 1}]});
    http.expectOne(nextUrl).flush({detail: 'Erreur'}, {status: 500, statusText: 'Server Error'});
    expect(failed).toBeTrue();
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
    const request = http.expectOne(`${environment.apiBaseUrl}client/trainings/`);
    expect(request.request.method).toBe('GET');
    request.flush({ count: 0, next: null, previous: null, results: [] });
  });
  it('records and validates session attendance', () => {
    service.recordAttendance(12, '2026-07-31', 'PRESENT', 'On time').subscribe();
    const record = http.expectOne(`${environment.apiBaseUrl}attendance/`);
    expect(record.request.body).toEqual({ enrollment: 12, date: '2026-07-31', status: 'PRESENT', note: 'On time' });
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
