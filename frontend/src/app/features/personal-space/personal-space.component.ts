import { AsyncPipe, NgIf } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { finalize } from 'rxjs';
import { ROLE_LABELS } from '../../core/models/auth.models';
import { AuthService } from '../../core/services/auth.service';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({ selector:'app-personal-space', standalone:true, imports:[AsyncPipe,NgIf,ReactiveFormsModule,MatButtonModule,MatCardModule,MatFormFieldModule,MatIconModule,MatInputModule,PageHeaderComponent], templateUrl:'./personal-space.component.html', styleUrl:'./personal-space.component.scss' })
export class PersonalSpaceComponent {
  readonly auth = inject(AuthService); readonly labels=ROLE_LABELS; private fb=inject(FormBuilder);
  readonly form=this.fb.nonNullable.group({current_password:['',Validators.required],new_password:['',[Validators.required,Validators.minLength(8)]],confirmation:['',Validators.required]});
  busy=false; success=''; error=''; hideCurrent=true; hideNew=true; hideConfirmation=true;
  submit(){ this.success=''; this.error=''; if(this.form.invalid){this.form.markAllAsTouched();return;} const v=this.form.getRawValue(); if(v.new_password!==v.confirmation){this.error='Les nouveaux mots de passe ne correspondent pas.';return;} this.busy=true; this.auth.changePassword({current_password:v.current_password,new_password:v.new_password}).pipe(finalize(()=>this.busy=false)).subscribe({next:r=>{this.success=r.detail;this.form.reset();},error:e=>this.error=e?.error?.current_password?.[0]||e?.error?.new_password?.[0]||'Le mot de passe n’a pas pu être modifié.'}); }
}
