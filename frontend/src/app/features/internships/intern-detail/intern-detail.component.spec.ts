import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { convertToParamMap, ActivatedRoute, Router } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of } from 'rxjs';

import { UserProfile } from '../../../core/models/auth.models';
import { InternProfile } from '../../../core/models/internship.models';
import { AuthService } from '../../../core/services/auth.service';
import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { InternshipService } from '../../../core/services/internship.service';
import { InternDetailComponent } from './intern-detail.component';

describe('InternDetailComponent supervisor journey', () => {
  let fixture: ComponentFixture<InternDetailComponent>;
  let component: InternDetailComponent;
  let internships: jasmine.SpyObj<InternshipService>;

  const supervisor: UserProfile = {
    id: 7, email: 'supervisor@test.com', first_name: 'Sara', last_name: 'Supervisor',
    full_name: 'Sara Supervisor', phone_number: '', role: 'EMPLOYEE',
  };
  const intern: InternProfile = {
    id: 11, user: 12, user_email: 'intern@test.com', user_full_name: 'Intern One',
    source_application: null, school: 'School', specialization: 'Security',
    internship_type: 'PFE', paid: false, business_unit: 2, business_unit_name: 'NetSEC',
    supervisor: 7, supervisor_email: 'supervisor@test.com', manager_name: 'Manager',
    subject_title: 'Security project', specification_pdf: null,
    internship_start: '2026-09-01', internship_end: '2026-12-01',
    current_status: 'ACTIVE', progress: 25, final_decision: '', documents: [],
    document_requirements: [], evaluations: [], created_at: '2026-09-01T00:00:00Z',
  };

  beforeEach(async () => {
    internships = jasmine.createSpyObj<InternshipService>('InternshipService', [
      'getIntern', 'updateIntern', 'createEvaluation',
    ]);
    internships.getIntern.and.returnValue(of(intern));
    internships.updateIntern.and.returnValue(of({ ...intern, progress: 50 }));
    internships.createEvaluation.and.returnValue(of({
      id: 1, intern: 11, evaluation_type: 'MIDTERM', technical_skills: 4,
      autonomy: 4, communication: 4, teamwork: 4, deadline_respect: 4,
      work_quality: 4, professionalism: 4, overall_score: 4, comments: '',
      evaluator: 7, evaluator_email: supervisor.email, created_at: '2026-09-12T00:00:00Z',
    }));
    await TestBed.configureTestingModule({
      imports: [InternDetailComponent],
      providers: [
        provideNoopAnimations(),
        { provide: AuthService, useValue: { currentUserSnapshot: supervisor } },
        { provide: InternshipService, useValue: internships },
        { provide: BusinessUnitService, useValue: jasmine.createSpyObj('BusinessUnitService', ['getBusinessUnits', 'getEligibleSupervisors']) },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: '11' }) } } },
        { provide: Router, useValue: jasmine.createSpyObj('Router', ['navigate']) },
        { provide: MatSnackBar, useValue: { open: jasmine.createSpy() } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(InternDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('shows assigned-intern tracking, documents and evaluation actions', () => {
    const content = fixture.nativeElement.textContent;
    expect(component.canSupervise).toBeTrue();
    expect(content).toContain('Suivi du stagiaire');
    expect(content).toContain('Documents obligatoires du stage');
    expect(content).toContain('Évaluations');
  });

  it('submits progress and an evaluation for the assigned intern', () => {
    component.progressForm.patchValue({ progress: 50 });
    component.saveProgress();
    component.evaluate();

    expect(internships.updateIntern).toHaveBeenCalledWith(11, jasmine.objectContaining({ progress: 50 }));
    expect(internships.createEvaluation).toHaveBeenCalledWith(jasmine.objectContaining({ intern: 11 }));
  });
});
