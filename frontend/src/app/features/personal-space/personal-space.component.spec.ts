import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { UserProfile } from '../../core/models/auth.models';
import { AuthService } from '../../core/services/auth.service';
import { PersonalSpaceComponent } from './personal-space.component';

describe('PersonalSpaceComponent', () => {
  let fixture: ComponentFixture<PersonalSpaceComponent>;
  let component: PersonalSpaceComponent;
  let auth: jasmine.SpyObj<AuthService> & { currentUser$: BehaviorSubject<UserProfile | null> };
  const user: UserProfile={id:1,email:'hr@test.com',first_name:'Hiba',last_name:'Test',full_name:'Hiba Test',phone_number:'+212600000000',role:'HR'};
  beforeEach(async()=>{auth=Object.assign(jasmine.createSpyObj<AuthService>('AuthService',['changePassword']),{currentUser$:new BehaviorSubject<UserProfile|null>(user)});await TestBed.configureTestingModule({imports:[PersonalSpaceComponent],providers:[{provide:AuthService,useValue:auth}]}).compileComponents();fixture=TestBed.createComponent(PersonalSpaceComponent);component=fixture.componentInstance;fixture.detectChanges();});
  it('renders real profile information as read-only text',()=>{expect(fixture.nativeElement.textContent).toContain('Hiba');expect(fixture.nativeElement.textContent).toContain('hr@test.com');expect(fixture.nativeElement.querySelector('input[type="email"]')).toBeNull();});
  it('rejects a password confirmation mismatch without an API call',()=>{component.form.setValue({current_password:'Current123!',new_password:'NewStrong456!',confirmation:'different'});component.submit();expect(auth.changePassword).not.toHaveBeenCalled();expect(component.error).toContain('ne correspondent pas');});
  it('shows success after a valid password change',()=>{auth.changePassword.and.returnValue(of({detail:'Mot de passe modifié avec succès.'}));component.form.setValue({current_password:'Current123!',new_password:'NewStrong456!',confirmation:'NewStrong456!'});component.submit();expect(auth.changePassword).toHaveBeenCalled();expect(component.success).toContain('succès');});
  it('shows an invalid-current-password error',()=>{auth.changePassword.and.returnValue(throwError(()=>({error:{current_password:['Le mot de passe actuel est incorrect.']}})));component.form.setValue({current_password:'Wrong123!',new_password:'NewStrong456!',confirmation:'NewStrong456!'});component.submit();expect(component.error).toContain('incorrect');});
});
