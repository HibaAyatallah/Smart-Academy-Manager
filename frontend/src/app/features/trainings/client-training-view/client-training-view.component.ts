import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { ClientTraining, SESSION_STATUS_LABELS } from '../../../core/models/training.models';
import { TrainingService } from '../../../core/services/training.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
@Component({selector:'app-client-training-view',standalone:true,imports:[CommonModule,MatButtonModule,MatCardModule,MatChipsModule,PageHeaderComponent],templateUrl:'./client-training-view.component.html',styleUrl:'./client-training-view.component.scss'})
export class ClientTrainingViewComponent implements OnInit { private readonly service=inject(TrainingService); readonly labels=SESSION_STATUS_LABELS; trainings:ClientTraining[]=[]; loading=true; error=''; ngOnInit(){this.service.getClientTrainings().subscribe({next:data=>{this.trainings=data.results;this.loading=false;},error:()=>{this.error='Impossible de charger vos formations.';this.loading=false;}});} safe(url:string){try{const parsed=new URL(url);return ['http:','https:'].includes(parsed.protocol)?url:'';}catch{return '';}} }
