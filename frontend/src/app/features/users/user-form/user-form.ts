import { NgFor, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { forkJoin, of } from 'rxjs';
import { finalize } from 'rxjs/operators';

import { ROLE_LABELS, UserProfile, UserRole } from '../../../core/models/auth.models';
import { BusinessUnit } from '../../../core/models/business-unit.models';
import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { UserManagementService, UserPayload } from '../../../core/services/user-management.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-user-form', standalone: true,
  imports: [MatButtonModule, MatCardModule, MatFormFieldModule, MatInputModule, MatProgressSpinnerModule, MatSelectModule, MatSlideToggleModule, NgFor, NgIf, PageHeaderComponent, ReactiveFormsModule, RouterLink],
  templateUrl: './user-form.html', styleUrl: './user-form.scss',
})
export class UserForm implements OnInit {
  private readonly formBuilder = inject(FormBuilder);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly service = inject(UserManagementService);
  private readonly buService = inject(BusinessUnitService);
  readonly roles = Object.keys(ROLE_LABELS) as UserRole[];
  readonly roleLabels = ROLE_LABELS;
  readonly form = this.formBuilder.nonNullable.group({
    email: ['', [Validators.required, Validators.email]], password: [''],
    first_name: [''], last_name: [''], phone_number: [''],
    role: ['EMPLOYEE' as UserRole, Validators.required],
    business_unit_id: [null as number | null], is_active: [true],
  });
  userId: number | null = null;
  businessUnits: BusinessUnit[] = [];
  isLoading = true; isSaving = false; errorMessage = '';
  get isEdit(): boolean { return this.userId !== null; }
  get supportsBusinessUnit(): boolean { return ['EMPLOYEE', 'BU_MANAGER'].includes(this.form.controls.role.value); }

  ngOnInit(): void {
    const rawId = this.route.snapshot.paramMap.get('id'); this.userId = rawId ? Number(rawId) : null;
    const userRequest = this.userId ? this.service.getUser(this.userId) : of(null);
    forkJoin({ user: userRequest, businessUnits: this.buService.getBusinessUnits({ is_active: true }) })
      .pipe(finalize(() => this.isLoading = false)).subscribe({
        next: ({ user, businessUnits }) => { this.businessUnits = businessUnits.results ?? []; if (user) this.populate(user); },
        error: () => this.errorMessage = 'Impossible de préparer le formulaire utilisateur.',
      });
  }

  save(): void {
    if (this.form.invalid || this.isSaving) { this.form.markAllAsTouched(); return; }
    const value = this.form.getRawValue();
    if (!this.isEdit && !value.password) { this.errorMessage = 'Le mot de passe est obligatoire.'; return; }
    const payload: UserPayload = { ...value, business_unit_id: this.supportsBusinessUnit ? value.business_unit_id : null };
    if (this.isEdit) delete payload.password;
    this.isSaving = true; this.errorMessage = '';
    const request = this.userId ? this.service.updateUser(this.userId, payload) : this.service.createUser(payload);
    request.pipe(finalize(() => this.isSaving = false)).subscribe({
      next: () => void this.router.navigateByUrl('/users'),
      error: error => { const messages = Object.values(error?.error ?? {}).flat().map(String); this.errorMessage = messages.join(' ') || "Impossible d'enregistrer l'utilisateur."; },
    });
  }

  private populate(user: UserProfile): void {
    this.form.patchValue({ email:user.email, first_name:user.first_name, last_name:user.last_name, phone_number:user.phone_number, role:user.role, is_active:user.is_active ?? true, business_unit_id:user.business_units?.[0]?.id ?? null });
  }
}
