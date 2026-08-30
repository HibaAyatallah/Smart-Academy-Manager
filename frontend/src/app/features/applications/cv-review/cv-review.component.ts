import { NgFor, NgIf } from '@angular/common';
import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { finalize } from 'rxjs/operators';
import { CVAnalysis, CVEducation, CVExperience } from '../../../core/models/application.models';
import { ApplicationService } from '../../../core/services/application.service';

@Component({
  selector: 'app-cv-review', standalone: true,
  imports: [NgFor, NgIf, ReactiveFormsModule, MatButtonModule, MatCardModule, MatFormFieldModule, MatIconModule, MatInputModule, MatProgressSpinnerModule, MatSnackBarModule],
  templateUrl: './cv-review.component.html', styleUrl: './cv-review.component.scss',
})
export class CVReviewComponent implements OnInit, OnChanges {
  @Input() applicationId: number | null = null;
  @Output() analysisSaved = new EventEmitter<CVAnalysis>();
  private readonly api = inject(ApplicationService); private readonly fb = inject(FormBuilder); private readonly snack = inject(MatSnackBar);
  activeApplicationId: number | null = null; analysis: CVAnalysis | null = null; loading = false; analyzing = false; saving = false; error = ''; success = '';
  readonly form = this.fb.group({
    first_name: ['', Validators.maxLength(150)], last_name: ['', Validators.maxLength(150)], email: ['', Validators.email], phone: [''], location: [''],
    skills: [''], languages: [''], certifications: [''], experiences: [''], education: [''],
  });
  ngOnInit(): void { this.resolveApplication(); }
  ngOnChanges(changes: SimpleChanges): void { if (changes['applicationId'] && !changes['applicationId'].firstChange) this.resolveApplication(); }
  private resolveApplication(): void {
    if (this.applicationId) { this.activeApplicationId = this.applicationId; this.loadApplication(); return; }
    this.loading = true;
    this.api.getMyApplications(1).pipe(finalize(() => this.loading = false)).subscribe({next:r => { this.activeApplicationId = r.results[0]?.id ?? null; if (this.activeApplicationId) this.loadApplication(); }, error:()=>this.error='Impossible de charger votre candidature.'});
  }
  private loadApplication(): void { if (!this.activeApplicationId) return; this.loading=true; this.api.getApplication(this.activeApplicationId).pipe(finalize(()=>this.loading=false)).subscribe({next:a=>{this.analysis=a.cv_analysis ?? null; if(a.cv_analysis)this.fill(a.cv_analysis);},error:()=>this.error='Impossible de charger les données du CV.'}); }
  upload(event: Event): void { const file=(event.target as HTMLInputElement).files?.[0]; if(!file||!this.activeApplicationId)return; this.analyzing=true;this.error='';this.success=''; this.api.uploadCV(this.activeApplicationId,file).pipe(finalize(()=>this.analyzing=false)).subscribe({next:r=>{this.analysis=r.analysis;if(r.analysis)this.fill(r.analysis);else this.error=r.analysis_error||'Le CV est conservé, mais son analyse a échoué.';},error:e=>this.error=e.error?.detail||e.error?.file?.[0]||'CV invalide ou analyse impossible.'}); }
  reanalyze(): void { if(!this.activeApplicationId)return; if(this.analysis?.human_validated&&!confirm('Cette action remplacera les données validées par une nouvelle extraction. Continuer ?'))return; this.analyzing=true;this.api.analyzeCV(this.activeApplicationId,true).pipe(finalize(()=>this.analyzing=false)).subscribe({next:a=>{this.analysis=a;this.fill(a);},error:e=>this.error=e.error?.detail||'Analyse impossible.'}); }
  save(validate=false): void { if(!this.activeApplicationId||this.form.invalid)return; this.saving=true; const data=this.payload(); const request=validate?this.api.validateCV(this.activeApplicationId,data):this.api.updateCVAnalysis(this.activeApplicationId,data); request.pipe(finalize(()=>this.saving=false)).subscribe({next:a=>{this.analysis=a;this.fill(a);this.analysisSaved.emit(a);this.success=validate?'Vos informations ont été enregistrées avec succès.':'Brouillon enregistré.';this.snack.open(this.success,'Fermer',{duration:3500});},error:e=>this.error=e.error?.detail||'Enregistrement impossible.'}); }
  private fill(a: CVAnalysis): void { this.form.patchValue({first_name:a.first_name,last_name:a.last_name,email:a.email,phone:a.phone,location:a.location,skills:a.skills.join('\n'),languages:a.languages.join('\n'),certifications:a.certifications.join('\n'),experiences:a.experiences.map(e=>[e.position,e.company,e.start_date,e.end_date,e.duration,e.description].join(' | ')).join('\n'),education:a.education.map(e=>[e.title,e.institution,e.start_date,e.end_date].join(' | ')).join('\n')}); }
  private lines(value:string|null|undefined){return (value||'').split('\n').map(v=>v.trim()).filter(Boolean);}
  private payload(): Partial<CVAnalysis> { const v=this.form.getRawValue(); const experiences:CVExperience[]=this.lines(v.experiences).map(line=>{const [position='',company='',start_date='',end_date='',duration='',description='']=line.split('|').map(x=>x.trim());return{position,company,start_date,end_date,duration,description};}); const education:CVEducation[]=this.lines(v.education).map(line=>{const[title='',institution='',start_date='',end_date='']=line.split('|').map(x=>x.trim());return{title,institution,start_date,end_date};}); return {first_name:v.first_name||'',last_name:v.last_name||'',full_name:`${v.first_name||''} ${v.last_name||''}`.trim(),email:v.email||'',phone:v.phone||'',location:v.location||'',skills:this.lines(v.skills),languages:this.lines(v.languages),certifications:this.lines(v.certifications),experiences,education,diplomas:education.map(e=>e.title).filter(Boolean),companies:[...new Set(experiences.map(e=>e.company).filter(Boolean))],positions:[...new Set(experiences.map(e=>e.position).filter(Boolean))]}; }
}
