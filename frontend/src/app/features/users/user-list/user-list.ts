import { NgFor, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatSelectModule } from '@angular/material/select';
import { MatTableModule } from '@angular/material/table';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs/operators';

import { ROLE_LABELS, UserProfile, UserRole } from '../../../core/models/auth.models';
import { UserManagementService } from '../../../core/services/user-management.service';
import { AuthService } from '../../../core/services/auth.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-user-list', standalone: true,
  imports: [MatButtonModule, MatCardModule, MatFormFieldModule, MatInputModule, MatPaginatorModule, MatProgressSpinnerModule, MatSelectModule, MatSnackBarModule, MatTableModule, NgFor, NgIf, PageHeaderComponent, ReactiveFormsModule, RouterLink],
  templateUrl: './user-list.html', styleUrl: './user-list.scss',
})
export class UserList implements OnInit {
  private readonly service = inject(UserManagementService);
  private readonly formBuilder = inject(FormBuilder);
  private readonly auth = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);
  readonly roles = Object.keys(ROLE_LABELS) as UserRole[];
  readonly roleLabels = ROLE_LABELS;
  readonly columns = ['name', 'email', 'role', 'business_unit', 'active', 'actions'];
  readonly filters = this.formBuilder.nonNullable.group({ search: [''], role: ['' as UserRole | ''], is_active: [''] });
  users: UserProfile[] = [];
  isLoading = true;
  errorMessage = '';
  total = 0;
  pageIndex = 0;
  readonly pageSize = 20;

  ngOnInit(): void { this.loadUsers(); }

  loadUsers(page = 1): void {
    this.isLoading = true; this.errorMessage = '';
    this.service.getUsers({ ...this.filters.getRawValue(), page }).pipe(finalize(() => this.isLoading = false)).subscribe({
      next: response => {
        this.users = response.results ?? [];
        this.total = response.count ?? this.users.length;
        this.pageIndex = page - 1;
      },
      error: () => this.errorMessage = 'Impossible de charger les utilisateurs.',
    });
  }

  reset(): void { this.filters.reset({ search: '', role: '', is_active: '' }); this.loadUsers(); }

  onPageChange(event: PageEvent): void { this.loadUsers(event.pageIndex + 1); }

  getRoleLabel(role: UserRole): string { return ROLE_LABELS[role]; }

  canDelete(user: UserProfile): boolean {
    const currentUser = this.auth.currentUserSnapshot;
    return currentUser?.role === 'SUPER_ADMIN'
      && currentUser.id !== user.id;
  }

  deleteUser(user: UserProfile): void {
    if (!this.canDelete(user) || !window.confirm(
      'Voulez-vous vraiment supprimer cet utilisateur ?'
    )) return;

    this.errorMessage = '';
    this.service.deleteUser(user.id).subscribe({
      next: () => {
        this.snackBar.open('Utilisateur supprimé avec succès.', 'Fermer', { duration: 3000 });
        const targetPage = this.users.length === 1 && this.pageIndex > 0
          ? this.pageIndex
          : this.pageIndex + 1;
        this.loadUsers(targetPage);
      },
      error: error => {
        this.errorMessage = error?.error?.detail
          || 'Impossible de supprimer cet utilisateur. Veuillez réessayer.';
      },
    });
  }

  toggleActive(user: UserProfile): void {
    this.service.updateUser(user.id, { is_active: !user.is_active }).subscribe({
      next: () => this.loadUsers(this.users.length === 1 && this.pageIndex > 0 ? this.pageIndex : this.pageIndex + 1),
      error: () => this.errorMessage = "Impossible de modifier l'état du compte.",
    });
  }
}
