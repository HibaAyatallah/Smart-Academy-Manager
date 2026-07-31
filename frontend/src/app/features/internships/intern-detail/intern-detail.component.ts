import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';import { MatCardModule } from '@angular/material/card';import { MatChipsModule } from '@angular/material/chips';import { MatFormFieldModule } from '@angular/material/form-field';import { MatInputModule } from '@angular/material/input';import { MatSelectModule } from '@angular/material/select';import { MatSlideToggleModule } from '@angular/material/slide-toggle';import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ActivatedRoute, Router } from '@angular/router';import { forkJoin } from 'rxjs';import { finalize } from 'rxjs/operators';
import { BusinessUnit } from '../../../core/models/business-unit.models';import { EVALUATION_TYPE_LABELS, INTERN_DOCUMENT_LABELS, INTERNSHIP_STATUS_LABELS, InternDocument, InternDocumentRequirement, InternProfile } from '../../../core/models/internship.models';import { UserProfile } from '../../../core/models/auth.models';
import { AuthService } from '../../../core/services/auth.service';import { BusinessUnitService } from '../../../core/services/business-unit.service';import { InternshipService } from '../../../core/services/internship.service';import { UserManagementService } from '../../../core/services/user-management.service';import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { dateRangeValidator } from '../../../core/utils/date-validators';

@Component({selector:'app-intern-detail',standalone:true,imports:[CommonModule,ReactiveFormsModule,MatButtonModule,MatCardModule,MatChipsModule,MatFormFieldModule,MatInputModule,MatSelectModule,MatSlideToggleModule,MatSnackBarModule,PageHeaderComponent],templateUrl:'./intern-detail.component.html',styleUrl:'./intern-detail.component.scss'})
export class InternDetailComponent implements OnInit {
 private readonly service=inject(InternshipService);private readonly auth=inject(AuthService);private readonly route=inject(ActivatedRoute);private readonly router=inject(Router);private readonly fb=inject(FormBuilder);private readonly snack=inject(MatSnackBar);private readonly buService=inject(BusinessUnitService);private readonly users=inject(UserManagementService);
 readonly statuses=INTERNSHIP_STATUS_LABELS;readonly documentLabels=INTERN_DOCUMENT_LABELS;readonly evaluationLabels=EVALUATION_TYPE_LABELS;intern:InternProfile|null=null;loading=true;saving=false;error='';
 readonly todayStr = (() => {
   const d = new Date();
   const year = d.getFullYear();
   const month = String(d.getMonth() + 1).padStart(2, '0');
   const day = String(d.getDate()).padStart(2, '0');
   return `${year}-${month}-${day}`;
 })();
 businessUnits:Array<Pick<BusinessUnit,'id'|'name'>>=[];supervisors:Array<Pick<UserProfile,'id'|'full_name'|'email'>>=[];selectedFile:File|null=null;selectedRequirement:InternDocumentRequirement|null=null;
 readonly adminForm = this.fb.group({
   business_unit: [null as number | null],
   supervisor: [null as number | null],
   school: [''],
   specialization: [''],
   internship_type: [''],
   paid: [false],
   subject_title: [''],
   internship_start: [''],
   internship_end: [''],
   current_status: ['UPCOMING'],
   progress: [0, [Validators.min(0), Validators.max(100)]],
   final_decision: ['']
 }, {
   validators: [dateRangeValidator('internship_start', 'internship_end')]
 });
 readonly progressForm=this.fb.nonNullable.group({current_status:['ACTIVE'],progress:[0,[Validators.min(0),Validators.max(100)]],final_decision:['']});
 readonly documentForm=this.fb.nonNullable.group({document_type:['CONVENTION'],comment:['']});
 readonly requirementForm=this.fb.nonNullable.group({name:['',Validators.required],description:[''],document_type:['OTHER'],is_required:[true],due_date:['']});
 readonly evaluationForm=this.fb.nonNullable.group({evaluation_type:['MIDTERM'],technical_skills:[0],autonomy:[0],communication:[0],teamwork:[0],deadline_respect:[0],work_quality:[0],professionalism:[0],comments:['']});
 get role(){return this.auth.currentUserSnapshot?.role;}get canAdmin(){return this.role==='SUPER_ADMIN';}get canSupervise(){return false;}get canUpload(){return this.canAdmin||this.role==='INTERN';}get canEvaluate(){return this.canAdmin;}
 ngOnInit(){const raw=this.route.snapshot.paramMap.get('id');if(raw==='me'){this.service.getInterns().subscribe({next:r=>{if(r.results[0])this.load(r.results[0].id);else{this.loading=false;this.error='Aucun dossier de stage ne vous est affecté.';}},error:()=>{this.loading=false;this.error='Dossier inaccessible.';}});return;}const id=Number(raw);if(!Number.isInteger(id)){this.router.navigate(['/internships']);return;}this.load(id);}
 load(id:number){this.loading=true;this.service.getIntern(id).pipe(finalize(()=>this.loading=false)).subscribe({next:i=>{this.intern=i;this.adminForm.patchValue(i as any);this.progressForm.patchValue({current_status:i.current_status,progress:i.progress,final_decision:i.final_decision});if(this.canAdmin)this.loadOptions();},error:()=>this.error='Dossier de stage introuvable ou inaccessible.'});}
 loadOptions(){forkJoin({bus:this.buService.getBusinessUnits(),users:this.users.getUsers({role:'EMPLOYEE',is_active:true})}).subscribe(({bus,users})=>{this.businessUnits=bus.results;this.supervisors=users.results;});}
 saveAdmin(){if(!this.intern||this.adminForm.invalid)return;this.save(this.adminForm.getRawValue() as any);}
 saveProgress(){if(!this.intern||this.progressForm.invalid)return;this.save(this.progressForm.getRawValue() as any);}
 private save(data:Partial<InternProfile>){this.saving=true;this.service.updateIntern(this.intern!.id,data).pipe(finalize(()=>this.saving=false)).subscribe({next:i=>{this.intern=i;this.notice('Dossier mis à jour.');},error:e=>this.notice(e.error?.detail??e.error?.internship_end?.[0]??'Mise à jour impossible.')});}
 fileSelected(event:Event,requirement:InternDocumentRequirement){this.selectedFile=(event.target as HTMLInputElement).files?.[0]??null;this.selectedRequirement=requirement;}
 upload(requirement:InternDocumentRequirement){if(!this.intern||!this.selectedFile||this.selectedRequirement?.id!==requirement.id)return;this.service.uploadDocument(this.intern.id,requirement.id,this.selectedFile).subscribe({next:()=>{this.selectedFile=null;this.selectedRequirement=null;this.notice('Document déposé.');this.load(this.intern!.id);},error:e=>this.notice(e.error?.file?.[0]??e.error?.detail??'Envoi impossible.')});}
 download(document:InternDocument){this.service.downloadDocument(document.id).subscribe({next:blob=>{const url=URL.createObjectURL(blob);window.open(url,'_blank','noopener');setTimeout(()=>URL.revokeObjectURL(url),60000);},error:()=>this.notice('Téléchargement impossible.')});}
 validate(document:InternDocument){const comment=window.prompt('Commentaire de validation (facultatif)')??'';this.service.validateDocument(document.id,comment).subscribe({next:()=>this.load(this.intern!.id),error:e=>this.notice(e.error?.detail??'Validation impossible.')});}
 reject(document:InternDocument){const comment=window.prompt('Motif du refus')??'';if(!comment)return;this.service.rejectDocument(document.id,comment).subscribe({next:()=>this.load(this.intern!.id),error:e=>this.notice(e.error?.comment?.[0]??'Refus impossible.')});}
 createRequirement(){if(this.requirementForm.invalid)return;const raw=this.requirementForm.getRawValue();this.service.createRequirement({...raw,due_date:raw.due_date||null} as any).subscribe({next:()=>{this.requirementForm.reset({name:'',description:'',document_type:'OTHER',is_required:true,due_date:''});this.notice('Document demandé ajouté.');this.load(this.intern!.id);},error:e=>this.notice(e.error?.detail??'Création impossible.')});}
 downloadSpecification(){if(!this.intern)return;this.service.downloadSpecification(this.intern.id).subscribe({next:blob=>{const url=URL.createObjectURL(blob);window.open(url,'_blank','noopener');setTimeout(()=>URL.revokeObjectURL(url),60000);},error:()=>this.notice('Cahier des charges indisponible.')});}
 evaluate(){if(!this.intern)return;const raw=this.evaluationForm.getRawValue();const scores=[raw.technical_skills,raw.autonomy,raw.communication,raw.teamwork,raw.deadline_respect,raw.work_quality,raw.professionalism];const overall_score=scores.reduce((a,b)=>a+b,0)/scores.length;this.service.createEvaluation({...raw,intern:this.intern.id,overall_score}).subscribe({next:()=>{this.notice('Évaluation enregistrée.');this.load(this.intern!.id);},error:e=>this.notice(e.error?.detail??'Évaluation impossible.')});}
 private notice(message:string){this.snack.open(message,'Fermer',{duration:4000});}
}
