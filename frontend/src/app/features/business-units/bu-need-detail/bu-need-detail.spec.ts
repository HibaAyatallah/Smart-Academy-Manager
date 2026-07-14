import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of } from 'rxjs';

import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { BuNeedDetail } from './bu-need-detail';

describe('BuNeedDetail', () => {
  let fixture: ComponentFixture<BuNeedDetail>;
  let service: jasmine.SpyObj<BusinessUnitService>;
  const need = { id: 8, business_unit: 3, business_unit_name: 'Data', title: 'Developer', description: 'Desc', need_type: 'HIRING', need_type_label: 'Hiring', required_skills: '', required_level: 'MID', required_level_label: 'Mid', number_of_profiles: 1, priority: 'MEDIUM', priority_label: 'Medium', expected_date: null, status: 'DRAFT', status_label: 'Draft', created_by: 1, created_by_email: 'hr@example.com', created_at: '', updated_at: '' } as any;

  beforeEach(async () => {
    service = jasmine.createSpyObj('BusinessUnitService', ['getNeed']);
    service.getNeed.and.returnValue(of(need));
    await TestBed.configureTestingModule({
      imports: [BuNeedDetail],
      providers: [
        provideRouter([]),
        { provide: BusinessUnitService, useValue: service },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: '3', needId: '8' }) } } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(BuNeedDetail);
  });

  it('creates and loads a need belonging to the route Business Unit', () => {
    fixture.detectChanges();
    expect(fixture.componentInstance).toBeTruthy();
    expect(service.getNeed).toHaveBeenCalledOnceWith(8);
    expect(fixture.componentInstance.need?.id).toBe(8);
    expect(fixture.componentInstance.isLoading).toBeFalse();
  });

  it('does not display a need belonging to another Business Unit', () => {
    service.getNeed.and.returnValue(of({ ...need, business_unit: 99 }));
    fixture.detectChanges();
    expect(fixture.componentInstance.need).toBeNull();
    expect(fixture.componentInstance.errorMessage).toContain("n'appartient pas");
  });
});
