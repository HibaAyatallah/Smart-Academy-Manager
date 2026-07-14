import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { BuList } from './bu-list';

describe('BuList', () => {
  let fixture: ComponentFixture<BuList>;
  let component: BuList;
  let service: jasmine.SpyObj<BusinessUnitService>;

  beforeEach(async () => {
    service = jasmine.createSpyObj('BusinessUnitService', ['getBusinessUnits']);
    service.getBusinessUnits.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    await TestBed.configureTestingModule({
      imports: [BuList],
      providers: [{ provide: BusinessUnitService, useValue: service }, provideRouter([])],
    }).compileComponents();
    fixture = TestBed.createComponent(BuList);
    component = fixture.componentInstance;
  });

  it('creates, loads, and exposes the empty state', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
    expect(service.getBusinessUnits).toHaveBeenCalled();
    expect(component.isLoading).toBeFalse();
    expect(component.businessUnits).toEqual([]);
    expect(component.total).toBe(0);
  });

  it('maps a successful paginated response', () => {
    service.getBusinessUnits.and.returnValue(of({
      count: 1, next: null, previous: null,
      results: [{ id: 1, name: 'Data', code: 'DATA', description: '', manager: 2, manager_email: 'm@example.com', manager_name: 'Manager', is_active: true, created_at: '', updated_at: '' }],
    }));
    fixture.detectChanges();
    expect(component.total).toBe(1);
    expect(component.businessUnits[0].code).toBe('DATA');
  });

  it('stops loading and reports an API error', () => {
    service.getBusinessUnits.and.returnValue(throwError(() => ({ status: 403 })));
    fixture.detectChanges();
    expect(component.isLoading).toBeFalse();
    expect(component.errorMessage).toContain('403');
  });

  it('requests the selected DRF page', () => {
    fixture.detectChanges();
    component.onPageChange({ pageIndex: 1, previousPageIndex: 0, pageSize: 20, length: 40 });
    expect(service.getBusinessUnits.calls.mostRecent().args[0]?.page).toBe(2);
  });
});
