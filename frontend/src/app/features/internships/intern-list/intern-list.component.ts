import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatPaginatorModule, PageEvent } from '@angular/material/paginator';
import { MatSelectModule } from '@angular/material/select';
import { RouterLink } from '@angular/router';
import { finalize } from 'rxjs/operators';
import { INTERNSHIP_STATUS_LABELS, InternProfile } from '../../../core/models/internship.models';
import { InternshipService } from '../../../core/services/internship.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';
@Component({selector:'app-intern-list',standalone:true,imports:[CommonModule,ReactiveFormsModule,RouterLink,MatButtonModule,MatCardModule,MatChipsModule,MatFormFieldModule,MatInputModule,MatPaginatorModule,MatSelectModule,PageHeaderComponent],templateUrl:'./intern-list.component.html',styleUrl:'./intern-list.component.scss'})
export class InternListComponent implements OnInit { private readonly service=inject(InternshipService);private readonly fb=inject(FormBuilder);readonly labels=INTERNSHIP_STATUS_LABELS;readonly filters=this.fb.nonNullable.group({search:[''],current_status:['']});interns:InternProfile[]=[];loading=true;error='';total=0;pageIndex=0;readonly pageSize=20;ngOnInit(){this.load();}load(page=1){this.loading=true;this.error='';this.service.getInterns({...this.filters.getRawValue(),page}).pipe(finalize(()=>this.loading=false)).subscribe({next:data=>{this.interns=data.results;this.total=data.count;this.pageIndex=page-1;},error:()=>this.error='Impossible de charger les stagiaires.'});}page(event:PageEvent){this.load(event.pageIndex+1);}}
