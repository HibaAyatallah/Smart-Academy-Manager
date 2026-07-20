import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { UserManagementService } from './user-management.service';

describe('UserManagementService', () => {
  let service: UserManagementService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(UserManagementService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('sends search, role and active filters to the existing users API', () => {
    service.getUsers({ search: 'hiba', role: 'EMPLOYEE', is_active: true }).subscribe();
    const request = http.expectOne(candidate => candidate.url === '/api/users/');
    expect(request.request.params.get('search')).toBe('hiba');
    expect(request.request.params.get('role')).toBe('EMPLOYEE');
    expect(request.request.params.get('is_active')).toBe('true');
    request.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('updates activation without calling the delete endpoint', () => {
    service.updateUser(7, { is_active: false }).subscribe();
    const request = http.expectOne('/api/users/7/');
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({ is_active: false });
    request.flush({ id: 7, is_active: false });
  });
});
