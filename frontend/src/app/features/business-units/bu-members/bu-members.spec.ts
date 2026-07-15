import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { BuMembers } from './bu-members';


describe('BuMembers', () => {
  let fixture: ComponentFixture<BuMembers>;
  let service: jasmine.SpyObj<BusinessUnitService>;

  beforeEach(async () => {
    service = jasmine.createSpyObj('BusinessUnitService', ['getMemberships']);
    service.getMemberships.and.returnValue(of({
      count: 1,
      next: null,
      previous: null,
      results: [{
        id: 1,
        business_unit: 4,
        business_unit_name: 'Data',
        user: 8,
        user_email: 'employee@example.com',
        user_name: 'Collaborateur Data',
        position: 'Développeur',
        joined_at: '2026-01-01',
        is_active: true,
      }],
    }));

    await TestBed.configureTestingModule({
      imports: [BuMembers],
      providers: [{ provide: BusinessUnitService, useValue: service }],
    }).compileComponents();
    fixture = TestBed.createComponent(BuMembers);
    fixture.detectChanges();
  });

  it('loads only active memberships exposed by the scoped API', () => {
    expect(service.getMemberships).toHaveBeenCalledOnceWith({ is_active: true });
    expect(fixture.nativeElement.textContent).toContain('Collaborateur Data');
    expect(fixture.nativeElement.textContent).toContain('employee@example.com');
  });
});
