import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { BuDetail } from './bu-detail';

describe('BuDetail', () => {
  let fixture: ComponentFixture<BuDetail>;
  let service: jasmine.SpyObj<BusinessUnitService>;

  beforeEach(async () => {
    service = jasmine.createSpyObj('BusinessUnitService', ['getBusinessUnit']);
    service.getBusinessUnit.and.returnValue(of({ id: 4, name: 'Data', code: 'DATA', description: '', manager: 2, manager_email: 'm@example.com', manager_name: 'Manager', is_active: true, created_at: '', updated_at: '' }));
    await TestBed.configureTestingModule({
      imports: [BuDetail],
      providers: [
        provideRouter([]),
        { provide: BusinessUnitService, useValue: service },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: '4' }) } } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(BuDetail);
  });

  it('creates and loads the requested Business Unit', () => {
    fixture.detectChanges();
    expect(fixture.componentInstance).toBeTruthy();
    expect(service.getBusinessUnit).toHaveBeenCalledOnceWith(4);
    expect(fixture.componentInstance.businessUnit?.code).toBe('DATA');
    expect(fixture.componentInstance.isLoading).toBeFalse();
  });

  it('shows the scoped not-found response', () => {
    service.getBusinessUnit.and.returnValue(throwError(() => ({ status: 404 })));
    fixture.detectChanges();
    expect(fixture.componentInstance.errorMessage).toContain("n'existe pas");
  });
});
