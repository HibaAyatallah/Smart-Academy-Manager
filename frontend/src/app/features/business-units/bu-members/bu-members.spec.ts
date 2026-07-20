import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { BuMembers } from './bu-members';


describe('BuMembers', () => {
  let fixture: ComponentFixture<BuMembers>;
  let service: jasmine.SpyObj<BusinessUnitService>;

  beforeEach(async () => {
    service = jasmine.createSpyObj('BusinessUnitService', [
      'createMembership', 'deleteMembership', 'getBusinessUnits', 'getMemberships',
    ]);
    service.getBusinessUnits.and.returnValue(of({
      count: 1, next: null, previous: null, results: [{
        id: 4, name: 'Data', code: 'DATA', description: '', manager: 2,
        manager_email: 'manager@example.com', manager_name: 'Manager',
        is_active: true, created_at: '', updated_at: '',
      }],
    }));
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

  it('adds an existing collaborator by email to the managed BU', () => {
    service.createMembership.and.returnValue(of({
      id: 2, business_unit: 4, business_unit_name: 'Data', user: 9,
      user_email: 'new@example.com', user_name: 'New Member', position: 'QA',
      joined_at: '2026-07-15', is_active: true,
    }));
    fixture.componentInstance.addForm.setValue({ member_email: 'new@example.com', position: 'QA' });

    fixture.componentInstance.addMember();

    expect(service.createMembership).toHaveBeenCalledWith(jasmine.objectContaining({
      business_unit: 4, member_email: 'new@example.com', position: 'QA',
    }));
  });

  it('removes the selected membership without navigating away', () => {
    service.deleteMembership.and.returnValue(of(void 0));
    const member = fixture.componentInstance.members[0];

    fixture.componentInstance.removeMember(member);

    expect(service.deleteMembership).toHaveBeenCalledOnceWith(1);
  });
});
