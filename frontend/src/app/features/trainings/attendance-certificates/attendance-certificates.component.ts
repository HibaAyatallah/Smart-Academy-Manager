import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { forkJoin } from 'rxjs';
import { ATTENDANCE_STATUS_LABELS, AttendanceStatus, SessionAttendance, TrainingCertificate, TrainingEnrollment } from '../../../core/models/training.models';
import { AuthService } from '../../../core/services/auth.service';
import { TrainingService } from '../../../core/services/training.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({selector:'app-attendance-certificates',standalone:true,imports:[CommonModule,FormsModule,MatButtonModule,MatCardModule,MatFormFieldModule,MatInputModule,MatSelectModule,MatSnackBarModule,PageHeaderComponent],templateUrl:'./attendance-certificates.component.html',styleUrl:'./attendance-certificates.component.scss'})
export class AttendanceCertificatesComponent implements OnInit {
  private readonly service=inject(TrainingService); private readonly auth=inject(AuthService); private readonly snack=inject(MatSnackBar);
  readonly labels=ATTENDANCE_STATUS_LABELS; readonly statuses=Object.keys(ATTENDANCE_STATUS_LABELS) as AttendanceStatus[];
  attendances:SessionAttendance[]=[]; enrollments:TrainingEnrollment[]=[]; certificates:TrainingCertificate[]=[]; loading=true; error=''; session='';
  get role(){return this.auth.currentUserSnapshot?.role;} get canManage(){return this.role==='SUPER_ADMIN'||this.role==='TRAINER_TUTOR';}
  ngOnInit(){this.load();}
  load(){this.loading=true;const filters=this.session?{enrollment__session:this.session}:{};forkJoin({attendance:this.service.getAttendance(filters),enrollments:this.service.getEnrollments(this.session?{session:this.session,status:'ENROLLED'}:{}),certificates:this.service.getCertificates(this.session?{enrollment__session:this.session}:{})}).subscribe({next:r=>{this.attendances=r.attendance.results;this.enrollments=r.enrollments.results;this.certificates=r.certificates.results;this.loading=false;},error:()=>{this.error='Impossible de charger les présences.';this.loading=false;}});}
  attendanceFor(id:number){return this.attendances.find(item=>item.enrollment===id);}
  save(enrollment:TrainingEnrollment,status:AttendanceStatus){const current=this.attendanceFor(enrollment.id);const call=current?this.service.updateAttendance(current.id,status,current.note):this.service.recordAttendance(enrollment.id,status);call.subscribe({next:()=>this.load(),error:e=>this.snack.open(e.error?.detail??'Action impossible.','Fermer',{duration:4000})});}
  validate(item:SessionAttendance){this.service.validateAttendance(item.id).subscribe({next:()=>this.load(),error:e=>this.snack.open(e.error?.detail??'Validation impossible.','Fermer',{duration:4000})});}
  completeSession(session:number){this.service.sessionAction(session,'complete').subscribe({next:()=>{this.snack.open('Session terminée et certificats générés.','Fermer',{duration:3500});this.load();},error:e=>this.snack.open(e.error?.detail??'Complétion impossible.','Fermer',{duration:5000})});}
  download(item:TrainingCertificate){this.service.downloadCertificate(item.id).subscribe(blob=>{const url=URL.createObjectURL(blob);const anchor=document.createElement('a');anchor.href=url;anchor.download=`${item.certificate_number}.pdf`;anchor.click();URL.revokeObjectURL(url);});}
}
