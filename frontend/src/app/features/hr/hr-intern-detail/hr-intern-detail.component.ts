import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { HRInternProfile } from '../../../core/models/internship.models';
import { InternshipService } from '../../../core/services/internship.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({ selector: 'app-hr-intern-detail', standalone: true, imports: [CommonModule, MatCardModule, MatChipsModule, PageHeaderComponent], templateUrl: './hr-intern-detail.component.html', styleUrl: './hr-intern-detail.component.scss' })
export class HrInternDetailComponent implements OnInit {
  private readonly route = inject(ActivatedRoute); private readonly service = inject(InternshipService);
  intern: HRInternProfile|null = null; loading = true; error = '';
  ngOnInit(): void { const id = Number(this.route.snapshot.paramMap.get('id')); this.service.getHRIntern(id).subscribe({ next: value => { this.intern = value; this.loading = false; }, error: () => { this.error = 'Dossier inaccessible.'; this.loading = false; } }); }
}
