import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { NeedStatus, NeedType } from '../../../core/models/business-unit.models';
import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { EmployeeTrainings } from './employee-trainings';

describe('EmployeeTrainings', () => {
  let fixture: ComponentFixture<EmployeeTrainings>;
  let service: jasmine.SpyObj<BusinessUnitService>;

  beforeEach(async () => {
    service = jasmine.createSpyObj('BusinessUnitService', ['getNeeds']);
    service.getNeeds.and.returnValue(of({
      count: 1,
      next: null,
      previous: null,
      results: [{
        id: 1,
        business_unit: 4,
        business_unit_name: 'Data',
        title: 'Formation Angular',
        description: '',
        need_type: NeedType.TRAINING,
        need_type_label: 'Formation',
        required_skills: '',
        required_level: 'MID' as any,
        required_level_label: '',
        number_of_profiles: 1,
        priority: 'MEDIUM' as any,
        priority_label: 'Moyenne',
        expected_date: null,
        training_start_date: '2026-09-10',
        training_end_date: null,
        training_link: 'https://example.com/formation',
        status: NeedStatus.CONFIRMED,
        status_label: 'Confirmé',
        created_by: 2,
        created_by_email: 'admin@example.com',
        created_at: '',
        updated_at: '',
      }],
    }));

    await TestBed.configureTestingModule({
      imports: [EmployeeTrainings],
      providers: [{ provide: BusinessUnitService, useValue: service }],
    }).compileComponents();
    fixture = TestBed.createComponent(EmployeeTrainings);
    fixture.detectChanges();
  });

  it('shows only the requested training columns without an internal details link', () => {
    expect(service.getNeeds).toHaveBeenCalledOnceWith({
      need_type: NeedType.TRAINING,
      status: NeedStatus.CONFIRMED,
    });
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('Formation Angular');
    expect(text).toContain('À définir');
    expect(text).not.toContain('Détails');
    expect(text).not.toContain('Priorité');
    expect(text).not.toContain('Statut');
  });

  it('opens the external training link in a new tab', () => {
    const link = fixture.nativeElement.querySelector('a[href="https://example.com/formation"]');
    expect(link?.getAttribute('target')).toBe('_blank');
    expect(link?.getAttribute('rel')).toContain('noopener');
  });
});
