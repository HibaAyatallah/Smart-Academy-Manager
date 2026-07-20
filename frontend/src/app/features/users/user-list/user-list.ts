import { NgFor, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs/operators';

import { ROLE_LABELS, UserProfile, UserRole } from '../../../core/models/auth.models';
import { UserManagementService } from '../../../core/services/user-management.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-user-list', standalone: true,
  imports: [MatButtonModule, MatCardModule, MatFormFieldModule, MatInputModule, MatProgressSpinnerModule, MatSelectModule, MatTableModule, NgFor, NgIf, PageHeaderComponent, ReactiveFormsModule, RouterLink],
  templateUrl: './user-list.html', styleUrl: './user-list.scss',
})
export class UserList implements OnInit {
  private readonly service = inject(UserManagementService);
  private readonly formBuilder = inject(FormBuilder);
  readonly roles = Object.keys(ROLE_LABELS) as UserRole[];
  readonly roleLabels = ROLE_LABELS;
  readonly columns = ['name', 'email', 'role', 'business_unit', 'active', 'actions'];
  readonly filters = this.formBuilder.nonNullable.group({ search: [''], role: ['' as UserRole | ''], is_active: [''] });
  users: UserProfile[] = [];
  isLoading = true;
  errorMessage = '';

  ngOnInit(): void { this.loadUsers(); }

  loadUsers(): void {
    this.isLoading = true; this.errorMessage = '';
    this.service.getUsers(this.filters.getRawValue()).pipe(finalize(() => this.isLoading = false)).subscribe({
      next: response => this.users = response.results ?? [],
      error: () => this.errorMessage = 'Impossible de charger les utilisateurs.',
    });
  }

  reset(): void { this.filters.reset({ search: '', role: '', is_active: '' }); this.loadUsers(); }

  getRoleLabel(role: UserRole): string { return ROLE_LABELS[role]; }

  toggleActive(user: UserProfile): void {
    this.service.updateUser(user.id, { is_active: !user.is_active }).subscribe({
      next: updated => this.users = this.users.map(item => item.id === updated.id ? updated : item),
      error: () => this.errorMessage = "Impossible de modifier l'état du compte.",
    });
  }
}
