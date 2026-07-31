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
      'getEnrollments', 'getAttendance', 'recordAttendance', 'updateAttendance',
    ]);
    service.getEnrollments.and.returnValue(of({
      count: 1, next: null, previous: null, results: [{
        id: 8, user: 3, user_email: 'employee@test.com', user_name: 'Sam Employee',
        training: 1, training_title: 'Angular avancé', project_name: 'Portail',
        business_unit: 4, session: 5, session_start_date: '2026-07-01',
        session_end_date: '2026-07-30', present_days: 1, requested_at: '',
        status: 'ENROLLED', final_status: 'ENROLLED', manager_comment: '',
        super_admin_comment: '', history: [],
      }],
    }));
    service.getAttendance.and.returnValue(of({
      count: 0, next: null, previous: null, results: [],
    }));

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
    expect(service.getEnrollments).toHaveBeenCalled();
    expect(service.getAttendance).toHaveBeenCalled();
    const text = fixture.nativeElement.textContent;
    expect(text).toContain('Angular avancé');
    expect(text).toContain('Portail');
    expect(text).toContain('Voir mon calendrier');
  });

  it('builds only the dates inside the session period', () => {
    fixture.componentInstance.openCalendar(fixture.componentInstance.trainings[0]);
    expect(fixture.componentInstance.days.length).toBe(30);
    expect(fixture.componentInstance.days[0].date).toBe('2026-07-01');
    expect(fixture.componentInstance.days[29].date).toBe('2026-07-30');
  });
});
