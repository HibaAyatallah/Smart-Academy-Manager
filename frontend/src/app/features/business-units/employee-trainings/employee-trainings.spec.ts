import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { TrainingService } from '../../../core/services/training.service';
import { EmployeeTrainings } from './employee-trainings';

describe('EmployeeTrainings', () => {
  let fixture: ComponentFixture<EmployeeTrainings>;
  let service: jasmine.SpyObj<TrainingService>;

  beforeEach(async () => {
    service = jasmine.createSpyObj('TrainingService', [
      'getAllEnrollments', 'getAllAttendance', 'recordAttendance', 'updateAttendance',
    ]);
    service.getAllEnrollments.and.returnValue(of(Array.from({ length: 25 }, (_, index) => ({
        id: index + 8, user: 3, user_email: 'employee@test.com', user_name: 'Sam Employee',
        training: index + 1, training_title: `Angular avancé ${index + 1}`, project_name: 'Portail',
        business_unit: 4, session: 5, session_start_date: '2026-07-01',
        session_end_date: '2026-07-30', present_days: 1, requested_at: '',
        status: 'ENROLLED' as const, final_status: 'ENROLLED' as const, manager_comment: '',
        super_admin_comment: '', history: [],
      }))));
    service.getAllAttendance.and.returnValue(of(Array.from({ length: 25 }, (_, index) => ({
      id: index + 1,
      enrollment: 8,
      session: 5,
      user_email: 'employee@test.com',
      user_name: 'Sam Employee',
      training_title: 'Angular avancé',
      date: `2026-07-${String(index + 1).padStart(2, '0')}`,
      status: 'PRESENT' as const,
      note: '',
      validated: false,
      validated_by: null,
      validated_by_email: null,
      validated_at: null,
      updated_at: '',
      history: [],
    }))));

    await TestBed.configureTestingModule({
      imports: [EmployeeTrainings],
      providers: [
        provideNoopAnimations(),
        { provide: TrainingService, useValue: service },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(EmployeeTrainings);
    fixture.detectChanges();
  });

  it('loads enrolled BU trainings as cards', () => {
    expect(service.getAllEnrollments).toHaveBeenCalled();
    expect(service.getAllAttendance).toHaveBeenCalled();
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('Angular avancé');
    expect(text).toContain('Portail');
    expect(text).toContain('Voir mon calendrier');
    expect(fixture.componentInstance.trainings.length).toBe(25);
  });

  it('builds only the dates inside the session period', () => {
    fixture.componentInstance.openCalendar(fixture.componentInstance.trainings[0]);
    expect(fixture.componentInstance.days.length).toBe(30);
    expect(fixture.componentInstance.days[0].date).toBe('2026-07-01');
    expect(fixture.componentInstance.days[29].date).toBe('2026-07-30');
  });

  it('uses all attendance records beyond the first DRF page', () => {
    expect(fixture.componentInstance.attendances.length).toBe(25);
    expect(fixture.componentInstance.presentDays(fixture.componentInstance.trainings[0])).toBe(25);
  });
});
