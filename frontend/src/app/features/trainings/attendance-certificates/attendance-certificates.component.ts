import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { forkJoin } from 'rxjs';
import { finalize } from 'rxjs/operators';
import { SessionAttendance, TrainingCertificate, TrainingEnrollment } from '../../../core/models/training.models';
import { AuthService } from '../../../core/services/auth.service';
import { TrainingService } from '../../../core/services/training.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({
  selector:'app-attendance-certificates',
  standalone:true,
  imports:[CommonModule,FormsModule,MatButtonModule,MatCardModule,MatFormFieldModule,MatIconModule,MatInputModule,MatSnackBarModule,PageHeaderComponent],
  templateUrl:'./attendance-certificates.component.html',
  styleUrl:'./attendance-certificates.component.scss',
})
export class AttendanceCertificatesComponent implements OnInit {
  private readonly service=inject(TrainingService);
  private readonly auth=inject(AuthService);
  private readonly snack=inject(MatSnackBar);
  attendances:SessionAttendance[]=[];
  enrollments:TrainingEnrollment[]=[];
  certificates:TrainingCertificate[]=[];
  days:string[]=[];
  loading=true;
  saving='';
  error='';
  session='';

  get role(){return this.auth.currentUserSnapshot?.role;}
  get canManage(){return this.role==='SUPER_ADMIN'||this.role==='BU_MANAGER'||this.role==='TRAINER_TUTOR';}

  ngOnInit(){this.load();}

  load(){
    this.loading=true; this.error='';
    const filters=this.session?{enrollment__session:this.session}:{};
    forkJoin({
      attendance:this.service.getAttendance(filters),
      enrollments:this.service.getEnrollments(this.session?{session:this.session}:{}),
      certificates:this.service.getCertificates(this.session?{enrollment__session:this.session}:{}),
    }).pipe(finalize(()=>this.loading=false)).subscribe({
      next:r=>{
        this.attendances=r.attendance.results;
        this.enrollments=r.enrollments.results.filter(item=>item.final_status==='ENROLLED'||item.final_status==='COMPLETED');
        this.certificates=r.certificates.results;
        this.days=this.session&&this.enrollments.length?this.dateRange(this.enrollments[0]):[];
      },
      error:()=>this.error='Impossible de charger les présences.',
    });
  }

  attendanceFor(enrollment:number,date:string){
    return this.attendances.find(item=>item.enrollment===enrollment&&item.date===date);
  }

  save(enrollment:TrainingEnrollment,date:string){
    const current=this.attendanceFor(enrollment.id,date);
    const next=current?.status==='PRESENT'?'ABSENT':'PRESENT';
    this.saving=`${enrollment.id}-${date}`;
    const call=current
      ?this.service.updateAttendance(current.id,next,current.note)
      :this.service.recordAttendance(enrollment.id,date,next);
    call.pipe(finalize(()=>this.saving='')).subscribe({
      next:item=>{this.upsert(item);this.snack.open('Présence corrigée.','Fermer',{duration:2200});},
      error:e=>this.snack.open(e.error?.detail??'Action impossible.','Fermer',{duration:4000}),
    });
  }

  validate(item:SessionAttendance){
    this.service.validateAttendance(item.id).subscribe({
      next:saved=>{this.upsert(saved);this.snack.open('Présence validée.','Fermer',{duration:2200});},
      error:e=>this.snack.open(e.error?.detail??'Validation impossible.','Fermer',{duration:4000}),
    });
  }

  totals(enrollment:number){
    const records=this.attendances.filter(item=>item.enrollment===enrollment);
    const present=records.filter(item=>item.status==='PRESENT'||item.status==='LATE').length;
    const absent=this.days.length-present;
    return {present,absent,rate:this.days.length?Math.round(100*present/this.days.length):0};
  }

  completeSession(session:number){
    this.service.sessionAction(session,'complete').subscribe({
      next:()=>{this.snack.open('Session terminée et certificats générés.','Fermer',{duration:3500});this.load();},
      error:e=>this.snack.open(e.error?.detail??'Complétion impossible.','Fermer',{duration:5000}),
    });
  }

  download(item:TrainingCertificate){
    this.service.downloadCertificate(item.id).subscribe(blob=>{
      const url=URL.createObjectURL(blob);const anchor=document.createElement('a');
      anchor.href=url;anchor.download=`${item.certificate_number}.pdf`;anchor.click();URL.revokeObjectURL(url);
    });
  }

  private upsert(item:SessionAttendance){
    const index=this.attendances.findIndex(value=>value.id===item.id);
    if(index>=0)this.attendances[index]=item;else this.attendances.push(item);
    this.attendances=[...this.attendances];
  }

  private dateRange(enrollment:TrainingEnrollment):string[]{
    const result:string[]=[];const cursor=new Date(`${enrollment.session_start_date}T00:00:00`);
    const end=new Date(`${enrollment.session_end_date}T00:00:00`);
    while(cursor<=end){
      result.push(`${cursor.getFullYear()}-${String(cursor.getMonth()+1).padStart(2,'0')}-${String(cursor.getDate()).padStart(2,'0')}`);
      cursor.setDate(cursor.getDate()+1);
    }
    return result;
  }
}
