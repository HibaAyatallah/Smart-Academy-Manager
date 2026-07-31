import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatChipsModule } from '@angular/material/chips';
import { InternshipService } from '../../../core/services/internship.service';
import { HRInternProfile } from '../../../core/models/internship.models';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({ selector: 'app-hr-intern-list', standalone: true, imports: [CommonModule, RouterLink, MatCardModule, MatChipsModule, PageHeaderComponent], templateUrl: './hr-intern-list.component.html', styleUrl: './hr-intern-list.component.scss' })
export class HrInternListComponent implements OnInit {
  private readonly service = inject(InternshipService);
  interns: HRInternProfile[] = []; loading = true; error = '';
  ngOnInit(): void { this.service.getHRInterns().subscribe({ next: response => { this.interns = response.results; this.loading = false; }, error: () => { this.error = 'Impossible de charger les stagiaires.'; this.loading = false; } }); }
}
