import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { BuNeedDetail } from './bu-need-detail';

describe('BuNeedDetail', () => {
  let fixture: ComponentFixture<BuNeedDetail>;
  let service: jasmine.SpyObj<BusinessUnitService>;

  const mockNeed = {
    id: 9,
    title: 'Besoin test',
    business_unit: 4,
    business_unit_name: 'BU 1',
    status: 'DRAFT' as any,
    priority: 'MEDIUM' as any,
    need_type: 'HIRING' as any,
    required_level: 'MID' as any,
    description: 'Description',
    required_skills: 'Skill A',
    number_of_profiles: 2,
    created_by: 2,
    created_by_email: 'm@example.com',
    created_at: '',
    updated_at: '',
    need_type_label: 'Embauche',
    required_level_label: 'Moyen',
    priority_label: 'Moyenne',
    status_label: 'Brouillon',
    expected_date: '',
  };

  function createComponent(needId: string, businessUnitId: string) {
    service = jasmine.createSpyObj('BusinessUnitService', ['getNeed']);
    service.getNeed.and.returnValue(of(mockNeed));
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [BuNeedDetail],
      providers: [
        provideRouter([]),
        { provide: BusinessUnitService, useValue: service },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: convertToParamMap({ id: businessUnitId, needId }) },
          },
        },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(BuNeedDetail);
    fixture.detectChanges();
    return fixture.componentInstance;
  }

  it('creates and loads the requested need', () => {
    const component = createComponent('9', '4');
    expect(component).toBeTruthy();
    expect(service.getNeed).toHaveBeenCalledOnceWith(9);
    expect(component.need?.title).toBe('Besoin test');
    expect(component.isLoading).toBeFalse();
  });

  it('shows the not-found response', () => {
    service = jasmine.createSpyObj('BusinessUnitService', ['getNeed']);
    service.getNeed.and.returnValue(throwError(() => ({ status: 404 })));
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      imports: [BuNeedDetail],
      providers: [
        provideRouter([]),
        { provide: BusinessUnitService, useValue: service },
        {
          provide: ActivatedRoute,
          useValue: {
            snapshot: { paramMap: convertToParamMap({ id: '4', needId: '999' }) },
          },
        },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(BuNeedDetail);
    fixture.detectChanges();
    expect(fixture.componentInstance.errorMessage).toContain("n'existe pas");
  });

  it('detects BU mismatch and shows an error', () => {
    const component = createComponent('9', '99');
    expect(component.errorMessage).toContain("n'appartient pas");
  });

  it('handles invalid need ID', () => {
    const component = createComponent('0', '4');
    expect(component.errorMessage).toContain('invalide');
    expect(component.isLoading).toBeFalse();
  });
});