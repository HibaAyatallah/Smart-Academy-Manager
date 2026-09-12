import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { TrainingService } from '../../../core/services/training.service';
import { UserManagementService } from '../../../core/services/user-management.service';
import { TrainingParticipantsComponent } from './training-participants.component';

describe('TrainingParticipantsComponent', () => {
  let fixture: ComponentFixture<TrainingParticipantsComponent>;
  let trainings: jasmine.SpyObj<TrainingService>;
  let users: jasmine.SpyObj<UserManagementService>;

  beforeEach(async () => {
    trainings = jasmine.createSpyObj('TrainingService', ['getEnrollments']);
    users = jasmine.createSpyObj('UserManagementService', ['getUser']);
    const enrollment = {
      id: 1, user: 7, user_email: 'hiba@example.com', user_name: 'Hiba Alaoui',
      training: 3, training_title: 'Angular avancé', session: 9,
      session_start_date: '2026-09-10', session_end_date: '2026-09-12',
      requested_at: '2026-08-04T10:00:00Z', status: 'ENROLLED', final_status: 'ENROLLED',
      project_name: '', business_unit: 1, present_days: 0, manager_comment: '', super_admin_comment: '', history: [],
    } as const;
    trainings.getEnrollments.and.returnValue(of({count: 25, next: '/api/enrollments/?page=2', previous: null, results: [enrollment]} as any));
    users.getUser.and.returnValue(of({
      id: 7, email: 'hiba@example.com', first_name: 'Hiba', last_name: 'Alaoui',
      full_name: 'Hiba Alaoui', phone_number: '', role: 'EMPLOYEE',
    }));
    await TestBed.configureTestingModule({
      imports: [TrainingParticipantsComponent],
      providers: [
        {provide: TrainingService, useValue: trainings},
        {provide: UserManagementService, useValue: users},
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(TrainingParticipantsComponent);
    fixture.detectChanges();
  });

  it('loads every enrollment page and displays real participant fields', () => {
    fixture.detectChanges();
    const text = fixture.nativeElement.textContent;
    expect(trainings.getEnrollments).toHaveBeenCalledOnceWith({page: 1});
    expect(users.getUser).toHaveBeenCalledOnceWith(7);
    expect(text).toContain('Hiba Alaoui');
    expect(text).toContain('hiba@example.com');
    expect(text).toContain('Collaborateur');
    expect(text).toContain('Angular avancé');
    expect(text).toContain('#9');
    expect(text).toContain('Inscrit');
  });

  it('loads the selected DRF page without accumulating duplicates', () => {
    fixture.componentInstance.page({pageIndex: 1, previousPageIndex: 0, pageSize: 20, length: 25});
    expect(trainings.getEnrollments).toHaveBeenCalledWith({page: 2});
    expect(fixture.componentInstance.pageIndex).toBe(1);
    expect(fixture.componentInstance.rows.length).toBe(1);
  });
});
