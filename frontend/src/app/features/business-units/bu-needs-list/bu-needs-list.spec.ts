import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { BuNeedsList } from './bu-needs-list';

describe('BuNeedsList', () => {
  let fixture: ComponentFixture<BuNeedsList>;
  let component: BuNeedsList;
  let service: jasmine.SpyObj<BusinessUnitService>;

  beforeEach(async () => {
    service = jasmine.createSpyObj('BusinessUnitService', ['getNeeds']);
    service.getNeeds.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    await TestBed.configureTestingModule({
      imports: [BuNeedsList],
      providers: [{ provide: BusinessUnitService, useValue: service }, provideRouter([])],
    }).compileComponents();
    fixture = TestBed.createComponent(BuNeedsList);
    component = fixture.componentInstance;
  });

  it('creates and loads the empty state', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
    expect(service.getNeeds).toHaveBeenCalled();
    expect(component.isLoading).toBeFalse();
    expect(component.needs).toEqual([]);
    expect(component.total).toBe(0);
  });

  it('maps a successful paginated response', () => {
    service.getNeeds.and.returnValue(of({
      count: 1, next: null, previous: null,
      results: [{ id: 1, title: 'Besoin test', business_unit: 1, business_unit_name: 'BU 1', status: 'DRAFT' as any, priority: 'MEDIUM' as any, need_type: 'HIRING' as any, required_level: 'MID' as any, description: '', required_skills: '', number_of_profiles: 1, created_by: 2, created_by_email: 'm@example.com', created_at: '', updated_at: '', need_type_label: 'Embauche', required_level_label: 'Moyen', priority_label: 'Moyenne', status_label: 'Brouillon', expected_date: '' }],
    }));
    fixture.detectChanges();
    expect(component.total).toBe(1);
    expect(component.needs[0].title).toBe('Besoin test');
  });

  it('stops loading and reports an API error', () => {
    service.getNeeds.and.returnValue(throwError(() => ({ status: 403 })));
    fixture.detectChanges();
    expect(component.isLoading).toBeFalse();
    expect(component.errorMessage).toContain('403');
  });

  it('requests the selected DRF page', () => {
    fixture.detectChanges();
    component.onPageChange({ pageIndex: 1, previousPageIndex: 0, pageSize: 20, length: 40 });
    expect(service.getNeeds.calls.mostRecent().args[0]?.page).toBe(2);
  });

  it('resets filters and reloads from page 1', () => {
    fixture.detectChanges();
    component.pageIndex = 3;
    component.resetFilters();
    expect(component.pageIndex).toBe(0);
    expect(service.getNeeds).toHaveBeenCalled();
  });

  it('applies filters and resets to page 1', () => {
    fixture.detectChanges();
    component.pageIndex = 2;
    component.filtersForm.patchValue({ status: 'DRAFT' as any });
    component.applyFilters();
    expect(component.pageIndex).toBe(0);
    expect(service.getNeeds.calls.mostRecent().args[0]?.status).toBe('DRAFT');
  });
});