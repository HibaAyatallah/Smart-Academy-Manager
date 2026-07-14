import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { BusinessUnitService } from './business-unit.service';

describe('BusinessUnitService', () => {
  let service: BusinessUnitService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(BusinessUnitService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('uses the centralized API URL without a double slash and maps pagination', () => {
    let count = -1;
    service.getBusinessUnits({ search: 'data', page: 2 }).subscribe((response) => count = response.count);
    const request = http.expectOne((candidate) => candidate.url === '/api/business-units/');
    expect(request.request.method).toBe('GET');
    expect(request.request.params.get('search')).toBe('data');
    expect(request.request.params.get('page')).toBe('2');
    request.flush({ count: 0, next: null, previous: null, results: [] });
    expect(count).toBe(0);
  });

  it('loads a Business Unit detail from the DRF detail endpoint', () => {
    service.getBusinessUnit(7).subscribe();
    const request = http.expectOne('/api/business-units/7/');
    expect(request.request.method).toBe('GET');
    request.flush({});
  });

  it('loads needs from the DRF paginated endpoint', () => {
    service.getNeeds({ business_unit: 7 }).subscribe();
    const request = http.expectOne((candidate) => candidate.url === '/api/business-unit-needs/');
    expect(request.request.params.get('business_unit')).toBe('7');
    request.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('loads a need detail from the correct endpoint', () => {
    service.getNeed(9).subscribe();
    const request = http.expectOne('/api/business-unit-needs/9/');
    expect(request.request.method).toBe('GET');
    request.flush({});
  });
});
