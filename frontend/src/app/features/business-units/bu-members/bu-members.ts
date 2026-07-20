import { DatePipe, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTableModule } from '@angular/material/table';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { forkJoin } from 'rxjs';
import { finalize } from 'rxjs/operators';

import { BusinessUnitMembership } from '../../../core/models/business-unit.models';
import { BusinessUnitService } from '../../../core/services/business-unit.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-bu-members',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatCardModule, MatFormFieldModule, MatInputModule, MatProgressSpinnerModule, MatSnackBarModule, MatTableModule, NgIf, PageHeaderComponent, ReactiveFormsModule],
  templateUrl: './bu-members.html',
  styleUrl: './bu-members.scss',
})
export class BuMembers implements OnInit {
  private readonly service = inject(BusinessUnitService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  readonly displayedColumns = ['name', 'email', 'position', 'joined_at', 'actions'];
  readonly searchForm = this.formBuilder.nonNullable.group({ search: [''] });
  readonly addForm = this.formBuilder.nonNullable.group({
    member_email: ['', [Validators.required, Validators.email]],
    position: [''],
  });
  members: BusinessUnitMembership[] = [];
  businessUnitId: number | null = null;
  isLoading = true;
  isSaving = false;
  errorMessage = '';

  ngOnInit(): void {
    this.loadInitialData();
  }

  search(): void {
    this.loadMembers();
  }

  resetSearch(): void {
    this.searchForm.reset({ search: '' });
    this.loadMembers();
  }

  addMember(): void {
    if (this.addForm.invalid || !this.businessUnitId || this.isSaving) {
      this.addForm.markAllAsTouched();
      return;
    }
    this.isSaving = true;
    this.errorMessage = '';
    this.service.createMembership({
      business_unit: this.businessUnitId,
      member_email: this.addForm.controls.member_email.value,
      position: this.addForm.controls.position.value,
      is_active: true,
    }).pipe(finalize(() => this.isSaving = false)).subscribe({
      next: () => {
        this.addForm.reset({ member_email: '', position: '' });
        this.snackBar.open('Collaborateur ajouté à votre Business Unit.', 'Fermer', { duration: 3000 });
        this.loadMembers();
      },
      error: error => this.errorMessage = this.apiError(error, "Impossible d'ajouter ce collaborateur."),
    });
  }

  removeMember(member: BusinessUnitMembership): void {
    this.service.deleteMembership(member.id).subscribe({
      next: () => {
        this.snackBar.open('Collaborateur retiré de votre Business Unit.', 'Fermer', { duration: 3000 });
        this.loadMembers();
      },
      error: error => this.errorMessage = this.apiError(error, 'Impossible de retirer ce collaborateur.'),
    });
  }

  private loadInitialData(): void {
    forkJoin({
      businessUnits: this.service.getBusinessUnits({ is_active: true }),
      memberships: this.service.getMemberships({ is_active: true }),
    }).pipe(
      finalize(() => this.isLoading = false),
    ).subscribe({
      next: ({ businessUnits, memberships }) => {
        this.businessUnitId = businessUnits.results?.[0]?.id ?? null;
        this.members = memberships.results ?? [];
      },
      error: () => this.errorMessage = 'Impossible de charger les membres de votre Business Unit.',
    });
  }

  private loadMembers(): void {
    this.isLoading = true;
    this.errorMessage = '';
    this.service.getMemberships({
      is_active: true,
      search: this.searchForm.controls.search.value,
    }).pipe(finalize(() => this.isLoading = false)).subscribe({
      next: response => this.members = response.results ?? [],
      error: () => this.errorMessage = 'Impossible de charger les membres de votre Business Unit.',
    });
  }

  private apiError(error: any, fallback: string): string {
    const messages = Object.values(error?.error ?? {}).flat().map(String).filter(Boolean);
    return messages.length ? messages.join(' ') : fallback;
  }
}
