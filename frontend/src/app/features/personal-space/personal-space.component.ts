import { AsyncPipe, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { Router } from '@angular/router';
import { finalize } from 'rxjs';
import { ROLE_LABELS } from '../../core/models/auth.models';
import { AuthService } from '../../core/services/auth.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';
import { LanguageService } from '../../core/i18n/language.service';
import { TranslatePipe } from '../../core/i18n/translate.pipe';

@Component({
  selector:'app-personal-space',
  standalone:true,
  imports:[AsyncPipe,NgIf,ReactiveFormsModule,MatButtonModule,MatCardModule,MatFormFieldModule,MatIconModule,MatInputModule,MatSnackBarModule,PageHeaderComponent,TranslatePipe],
  templateUrl:'./personal-space.component.html',
  styleUrl:'./personal-space.component.scss',
})
export class PersonalSpaceComponent implements OnInit {
  readonly auth=inject(AuthService); readonly labels=ROLE_LABELS;
  private readonly fb=inject(FormBuilder); private readonly snack=inject(MatSnackBar); private readonly router=inject(Router);
  private readonly language=inject(LanguageService);
  readonly contactForm=this.fb.nonNullable.group({
    email:['',[Validators.required,Validators.email]],
    phone_number:['',[Validators.pattern(/^\+?[0-9][0-9 .()-]{6,30}$/)]],
    current_password:['',Validators.required],
  });
  readonly passwordForm=this.fb.nonNullable.group({
    current_password:['',Validators.required],
    new_password:['',[Validators.required,Validators.minLength(8)]],
    confirmation:['',Validators.required],
  });
  contactBusy=false; passwordBusy=false; contactError=''; passwordError='';

  ngOnInit(){const user=this.auth.currentUserSnapshot;if(user)this.contactForm.patchValue({email:user.email,phone_number:user.phone_number});}

  saveContact(){
    this.contactError='';if(this.contactForm.invalid){this.contactForm.markAllAsTouched();return;}
    this.contactBusy=true;
    this.auth.updateContactDetails(this.contactForm.getRawValue()).pipe(finalize(()=>this.contactBusy=false)).subscribe({
      next:user=>{this.contactForm.patchValue({email:user.email,phone_number:user.phone_number,current_password:''});this.snack.open(this.language.translate('profile.contactSaved'),this.language.translate('common.close'),{duration:3000});},
      error:e=>this.contactError=e.error?.email?.[0]??e.error?.phone_number?.[0]??e.error?.current_password?.[0]??this.language.translate('profile.failed'),
    });
  }

  changePassword(){
    this.passwordError='';if(this.passwordForm.invalid){this.passwordForm.markAllAsTouched();return;}
    const value=this.passwordForm.getRawValue();
    if(value.new_password!==value.confirmation){this.passwordError=this.language.translate('profile.mismatch');return;}
    if(!window.confirm(this.language.translate('profile.confirmChange')))return;
    this.passwordBusy=true;
    this.auth.changePassword(value).pipe(finalize(()=>this.passwordBusy=false)).subscribe({
      next:()=>{this.auth.logout(false);void this.router.navigateByUrl('/connexion');},
      error:e=>this.passwordError=e.error?.current_password?.[0]??e.error?.new_password?.[0]??e.error?.confirmation?.[0]??this.language.translate('profile.failed'),
    });
  }
}
