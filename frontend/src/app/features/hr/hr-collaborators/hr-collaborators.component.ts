import { CommonModule } from '@angular/common';
import { Component, OnInit, inject } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { HRBusinessUnitGroup } from '../../../core/models/internship.models';
import { InternshipService } from '../../../core/services/internship.service';
import { PageHeaderComponent } from '../../../shared/components/page-header/page-header.component';

@Component({ selector: 'app-hr-collaborators', standalone: true, imports: [CommonModule, MatCardModule, PageHeaderComponent], templateUrl: './hr-collaborators.component.html', styleUrl: './hr-collaborators.component.scss' })
export class HrCollaboratorsComponent implements OnInit {
  private readonly service = inject(InternshipService); groups: HRBusinessUnitGroup[] = []; loading = true; error = '';
  ngOnInit(): void { this.service.getHRGroups().subscribe({ next: groups => { this.groups = groups; this.loading = false; }, error: () => { this.error = 'Impossible de charger les collaborateurs.'; this.loading = false; } }); }
}
