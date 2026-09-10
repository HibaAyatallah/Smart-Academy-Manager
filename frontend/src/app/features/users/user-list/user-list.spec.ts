import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';

import { AuthService } from '../../../core/services/auth.service';
import { UserManagementService } from '../../../core/services/user-management.service';
import { UserList } from './user-list';

describe('UserList deletion', () => {
  let service: jasmine.SpyObj<UserManagementService>;

  beforeEach(async () => {
    service = jasmine.createSpyObj<UserManagementService>(
      'UserManagementService', ['getUsers', 'deleteUser', 'updateUser'],
    );
    service.getUsers.and.returnValue(of({ count: 1, next: null, previous: null, results: [] }));
    service.deleteUser.and.returnValue(of(void 0));

    await TestBed.configureTestingModule({
      imports: [UserList],
      providers: [
        provideRouter([]),
        { provide: UserManagementService, useValue: service },
        { provide: AuthService, useValue: { currentUserSnapshot: { id: 1, role: 'SUPER_ADMIN' } } },
        { provide: MatSnackBar, useValue: { open: jasmine.createSpy('open') } },
      ],
    }).compileComponents();
  });

  it('reloads the API list only after DELETE succeeds', () => {
    const fixture = TestBed.createComponent(UserList);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    service.getUsers.calls.reset();
    component.users = [{ id: 7 } as never, { id: 8 } as never];
    component.pageIndex = 1;
    spyOn(window, 'confirm').and.returnValue(true);

    component.deleteUser({ id: 7 } as never);

    expect(service.deleteUser).toHaveBeenCalledOnceWith(7);
    expect(service.getUsers).toHaveBeenCalledWith(jasmine.objectContaining({ page: 2 }));
  });

  it('keeps the list unchanged when DELETE fails', () => {
    service.deleteUser.and.returnValue(throwError(() => ({ error: { detail: 'Suppression refusée.' } })));
    const fixture = TestBed.createComponent(UserList);
    const component = fixture.componentInstance;
    fixture.detectChanges();
    service.getUsers.calls.reset();
    component.users = [{ id: 7 } as never];
    spyOn(window, 'confirm').and.returnValue(true);

    component.deleteUser({ id: 7 } as never);

    expect(service.getUsers).not.toHaveBeenCalled();
    expect(component.users.length).toBe(1);
    expect(component.errorMessage).toBe('Suppression refusée.');
  });
});
