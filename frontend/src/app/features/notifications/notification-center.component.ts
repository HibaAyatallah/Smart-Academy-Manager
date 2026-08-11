import { DatePipe, NgFor, NgIf } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar, MatSnackBarModule } from '@angular/material/snack-bar';
import { RouterLink } from '@angular/router';
import { finalize, forkJoin } from 'rxjs';

import { AppNotification, NotificationPreferences } from '../../core/models/notification.models';
import { NotificationService } from '../../core/services/notification.service';
import { EmptyStateComponent } from '../../shared/components/empty-state/empty-state.component';
import { PageHeaderComponent } from '../../shared/components/page-header/page-header.component';

@Component({
  selector: 'app-notification-center', standalone: true,
  imports: [DatePipe, FormsModule, MatButtonModule, MatCardModule, MatCheckboxModule, MatIconModule,
    MatProgressSpinnerModule, MatSnackBarModule, NgFor, NgIf, RouterLink, EmptyStateComponent, PageHeaderComponent],
  templateUrl: './notification-center.component.html', styleUrl: './notification-center.component.scss',
})
export class NotificationCenterComponent implements OnInit {
  private readonly service=inject(NotificationService);private readonly snack=inject(MatSnackBar);
  notifications:AppNotification[]=[];preferences?:NotificationPreferences;loading=true;saving=false;error='';
  readonly preferenceFields:Array<{key:keyof NotificationPreferences;label:string}>=[
    {key:'approvals',label:'Approbations'},{key:'assignments',label:'Affectations'},
    {key:'sessions',label:'Sessions'},{key:'evaluations',label:'Évaluations'},
    {key:'documents',label:'Documents'},{key:'certificates',label:'Certificats'},
  ];
  ngOnInit(){this.load();}
  load(){this.loading=true;this.error='';forkJoin({items:this.service.list(),preferences:this.service.getPreferences()}).pipe(finalize(()=>this.loading=false)).subscribe({next:r=>{this.notifications=r.items.results;this.preferences=r.preferences;},error:()=>this.error='Impossible de charger les notifications.'});}
  read(item:AppNotification){if(item.is_read)return;this.service.markRead(item.id).subscribe({next:value=>Object.assign(item,value),error:()=>this.snack.open('Mise à jour impossible.','Fermer',{duration:3000})});}
  readAll(){this.service.markAllRead().subscribe({next:()=>{this.notifications=this.notifications.map(item=>({...item,is_read:true,read_at:item.read_at??new Date().toISOString()}));this.snack.open('Toutes les notifications sont lues.','Fermer',{duration:3000});},error:()=>this.snack.open('Action impossible.','Fermer',{duration:3000})});}
  savePreferences(){if(!this.preferences||this.saving)return;this.saving=true;this.service.updatePreferences(this.preferences).pipe(finalize(()=>this.saving=false)).subscribe({next:value=>{this.preferences=value;this.snack.open('Préférences enregistrées.','Fermer',{duration:3000});},error:()=>this.snack.open('Enregistrement impossible.','Fermer',{duration:3000})});}
}
