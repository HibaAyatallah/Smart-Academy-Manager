import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize } from 'rxjs/operators';
import { DELIVERABLE_STATUS_LABELS, PROJECT_STATUS_LABELS, Project, ProjectDeliverable, ProjectDocument, ProjectOptions } from '../../../core/models/project.models';
import { AuthService } from '../../../core/services/auth.service';
import { ProjectService } from '../../../core/services/project.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
import { minTodayValidator, dateRangeValidator } from '../../../core/utils/date-validators';

@Component({
  selector: 'app-project-detail',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule, MatButtonModule, MatCardModule, MatChipsModule, MatFormFieldModule, MatInputModule, MatSelectModule, MatSnackBarModule, PageHeaderComponent],
  templateUrl: './project-detail.component.html',
  styleUrl: './project-detail.component.scss'
})
export class ProjectDetailComponent implements OnInit {
  private readonly service = inject(ProjectService);
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private readonly fb = inject(FormBuilder);
  private readonly snack = inject(MatSnackBar);
  readonly projectLabels = PROJECT_STATUS_LABELS;
  readonly deliverableLabels = DELIVERABLE_STATUS_LABELS;
  project: Project | null = null;
  options: ProjectOptions = { business_units: [], supervisors: [], assignees: [] };
  loading = true;
  saving = false;
  error = '';
  isNew = false;
  selectedFile: File | null = null;
  readonly todayStr = (() => {
    const d = new Date();
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  })();

  readonly form = this.fb.nonNullable.group({
    title: ['', Validators.required],
    description: ['', Validators.required],
    business_unit: [null as number | null, Validators.required],
    supervisor: [null as number | null, Validators.required],
    assignee_ids: [[] as number[]],
    start_date: ['', [minTodayValidator()]],
    end_date: ['', [minTodayValidator()]],
    status: ['PLANNED'],
    progress: [0, [Validators.min(0), Validators.max(100)]]
  }, {
    validators: [dateRangeValidator('start_date', 'end_date')]
  });

  readonly deliverableForm = this.fb.nonNullable.group({
    title: ['', Validators.required],
    description: [''],
    due_date: ['', [minTodayValidator()]]
  });

  readonly commentForm = this.fb.nonNullable.group({
    content: ['', Validators.required]
  });
get role(){return this.auth.currentUserSnapshot?.role;}get isSupervisor(){return this.project?.supervisor===this.auth.currentUserSnapshot?.id;}get canManage(){return this.role==='SUPER_ADMIN'||this.isSupervisor||this.isNew;}ngOnInit(){
    const raw = this.route.snapshot.paramMap.get('id');
    // No 'id' param or 'new' indicates create mode '/projects/new'
    if (!raw || raw === 'new') {
      this.isNew = true;
      this.loading = false;
      this.loadOptions();
      return;
    }
    const id = Number(raw);
    if (!Number.isInteger(id)) {
      this.router.navigate(['/projects']);
      return;
    }
    this.load(id);
  }
load(id:number){this.loading=true;this.service.getProject(id).pipe(finalize(()=>this.loading=false)).subscribe({next:p=>{this.project=p;this.form.patchValue({...p,assignee_ids:p.assignees.map(a=>a.id)} as any);if(this.canManage)this.loadOptions();},error:()=>this.error='Projet introuvable ou inaccessible.'});}loadOptions(){this.service.getOptions().subscribe({next:o=>{this.options=o;if(this.role==='EMPLOYEE'&&this.isNew){this.form.patchValue({supervisor:this.auth.currentUserSnapshot?.id??null});}},error:()=>this.error='Options d\'affectation indisponibles.'});}
save(){if(this.form.invalid)return;this.saving=true;const data=this.form.getRawValue() as unknown as Record<string,unknown>;const request=this.isNew?this.service.createProject(data):this.service.updateProject(this.project!.id,data);request.pipe(finalize(()=>this.saving=false)).subscribe({next:p=>{this.notice('Projet enregistré.');this.router.navigate(['/projects',p.id]);if(!this.isNew)this.load(p.id);},error:e=>this.notice(this.apiError(e))});}
addDeliverable(){if(!this.project||this.deliverableForm.invalid)return;this.service.createDeliverable({project:this.project.id,...this.deliverableForm.getRawValue()}).subscribe({next:()=>{this.deliverableForm.reset();this.load(this.project!.id);},error:e=>this.notice(this.apiError(e))});}setDeliverable(deliverable:ProjectDeliverable,status:string){this.service.updateDeliverable(deliverable.id,{status}).subscribe({next:()=>this.load(this.project!.id),error:e=>this.notice(this.apiError(e))});}
addComment(){if(!this.project||this.commentForm.invalid)return;this.service.addComment(this.project.id,this.commentForm.controls.content.value).subscribe({next:()=>{this.commentForm.reset();this.load(this.project!.id);},error:e=>this.notice(this.apiError(e))});}fileSelected(e:Event){this.selectedFile=(e.target as HTMLInputElement).files?.[0]??null;}upload(){if(!this.project||!this.selectedFile)return;this.service.uploadDocument(this.project.id,this.selectedFile).subscribe({next:()=>{this.selectedFile=null;this.load(this.project!.id);},error:e=>this.notice(this.apiError(e))});}download(document:ProjectDocument){this.service.downloadDocument(document.id).subscribe({next:blob=>{const url=URL.createObjectURL(blob);window.open(url,'_blank','noopener');setTimeout(()=>URL.revokeObjectURL(url),60000);},error:()=>this.notice('Téléchargement impossible.')});}private apiError(e:any){const data=e.error;if(typeof data?.detail==='string')return data.detail;const first=data&&Object.values(data)[0];return Array.isArray(first)?String(first[0]):'Action impossible.';}private notice(message:string){this.snack.open(message,'Fermer',{duration:4000});}}
