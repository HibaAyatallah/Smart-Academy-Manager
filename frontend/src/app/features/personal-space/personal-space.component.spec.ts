import { provideNoopAnimations } from '@angular/platform-browser/animations';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';
import { UserProfile } from '../../core/models/auth.models';
import { AuthService } from '../../core/services/auth.service';
import { PersonalSpaceComponent } from './personal-space.component';

describe('PersonalSpaceComponent', () => {
  let fixture:ComponentFixture<PersonalSpaceComponent>;let component:PersonalSpaceComponent;
  let auth:jasmine.SpyObj<AuthService>&{currentUser$:BehaviorSubject<UserProfile|null>;currentUserSnapshot:UserProfile};
  const user:UserProfile={id:1,email:'hr@test.com',first_name:'Hiba',last_name:'Test',full_name:'Hiba Test',phone_number:'+212600000000',role:'HR'};
  beforeEach(async()=>{
    auth=Object.assign(jasmine.createSpyObj<AuthService>('AuthService',['changePassword','updateContactDetails','logout']),{currentUser$:new BehaviorSubject<UserProfile|null>(user),currentUserSnapshot:user});
    auth.updateContactDetails.and.returnValue(of(user));auth.changePassword.and.returnValue(of({detail:'OK'}));
    await TestBed.configureTestingModule({imports:[PersonalSpaceComponent],providers:[provideNoopAnimations(),{provide:AuthService,useValue:auth},{provide:Router,useValue:{navigateByUrl:jasmine.createSpy().and.resolveTo(true)}}]}).compileComponents();
    fixture=TestBed.createComponent(PersonalSpaceComponent);component=fixture.componentInstance;fixture.detectChanges();
  });
  it('edits only contact details with the current password',()=>{component.contactForm.setValue({email:'new@test.com',phone_number:'+212611111111',current_password:'Current123!'});component.saveContact();expect(auth.updateContactDetails).toHaveBeenCalled();});
  it('rejects a password confirmation mismatch',()=>{component.passwordForm.setValue({current_password:'Current123!',new_password:'NewStrong456!',confirmation:'different'});component.changePassword();expect(auth.changePassword).not.toHaveBeenCalled();expect(component.passwordError).toContain('correspondent');});
  it('logs out after a confirmed password change',()=>{spyOn(window,'confirm').and.returnValue(true);component.passwordForm.setValue({current_password:'Current123!',new_password:'NewStrong456!',confirmation:'NewStrong456!'});component.changePassword();expect(auth.changePassword).toHaveBeenCalled();expect(auth.logout).toHaveBeenCalledWith(false);});
});
