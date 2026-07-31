import { Component, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UserImportService, ImportPreviewResult, ImportConfirmResult } from '../../../core/services/user-import.service';
import { HttpErrorResponse } from '@angular/common/http';
import { saveAs } from 'file-saver';
import * as Papa from 'papaparse';
import { MatStepperModule, MatStepper } from '@angular/material/stepper';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatTooltipModule } from '@angular/material/tooltip';

@Component({
  selector: 'app-bulk-import',
  standalone: true,
  imports: [CommonModule, MatStepperModule, MatButtonModule, MatIconModule, MatProgressBarModule, MatTooltipModule],
  templateUrl: './bulk-import.component.html',
  styleUrls: ['./bulk-import.component.scss']
})
export class BulkImportComponent {
  @ViewChild('stepper') stepper!: MatStepper;
  
  file: File | null = null;
  previewData: ImportPreviewResult | null = null;
  importResult: ImportConfirmResult | null = null;
  isLoading = false;
  errorMessage = '';
  activeTab: 'valid' | 'invalid' | 'skipped' = 'valid';

  createMissingBus = false;

  get stats() {
    let collaborateurs = 0;
    let stagiaires = 0;
    
    if (this.previewData && this.previewData.valid_rows) {
      this.previewData.valid_rows.forEach(row => {
        const role = row.payload.role;
        if (role === 'INTERN') {
          stagiaires++;
        } else if (['EMPLOYEE', 'BU_MANAGER', 'TRAINER_TUTOR'].includes(role)) {
          collaborateurs++;
        }
      });
    }
    
    return {
      collaborateurs,
      stagiaires,
      total: this.previewData?.valid_count || 0
    };
  }

  constructor(private userImportService: UserImportService) {}

  onFileSelected(event: any) {
    const file = event.target.files[0];
    if (file) {
      this.file = file;
      this.errorMessage = '';
    }
  }

  onDragOver(event: any) {
    event.preventDefault();
  }

  onDrop(event: any) {
    event.preventDefault();
    const file = event.dataTransfer.files[0];
    if (file) {
      this.file = file;
      this.errorMessage = '';
    }
  }

  uploadFile() {
    if (!this.file) return;
    this.isLoading = true;
    this.errorMessage = '';
    
    this.userImportService.previewImport(this.file).subscribe({
      next: (res) => {
        this.previewData = res;
        this.isLoading = false;
        // Default createMissingBus to false when new file uploaded
        this.createMissingBus = false;
        
        if (this.previewData.valid_count > 0) {
          this.activeTab = 'valid';
        } else if (this.previewData.invalid_count > 0) {
          this.activeTab = 'invalid';
        }
        setTimeout(() => this.stepper.next(), 100);
      },
      error: (err: HttpErrorResponse) => {
        this.isLoading = false;
        this.errorMessage = err.error?.error || err.message || 'Erreur système inconnue.';
      }
    });
  }

  confirmImport() {
    if (!this.previewData || this.previewData.valid_rows.length === 0) return;
    
    this.isLoading = true;
    this.errorMessage = '';
    
    this.userImportService.confirmImport(this.previewData.valid_rows, this.createMissingBus).subscribe({
      next: (res) => {
        this.isLoading = false;
        this.importResult = res;
        setTimeout(() => this.stepper.next(), 100);
      },
      error: (err: HttpErrorResponse) => {
        this.isLoading = false;
        this.errorMessage = err.error?.error || "Erreur lors de l'importation.";
      }
    });
  }

  downloadResult() {
    if (!this.importResult || !this.importResult.results) return;
    
    const csv = Papa.unparse(this.importResult.results);
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
    saveAs(blob, 'resultat_import.csv');
  }

  downloadTemplate() {
    const template = [
      {
        Prénom: 'Jean',
        Nom: 'Dupont',
        Email: 'jean.dupont@personal.com',
        Tél: '+33600000000',
        Profil: 'EMPLOYEE',
        BU: 'BU_IT',
        Poste: 'Développeur',
        Superviseur: '',
        Ecole: '',
        Specialité: '',
        'Type de stage': '',
        'Début de stage': '',
        'Fin de stage': '',
        'Rémunéré': '',
        Sujet: ''
      }
    ];
    const csv = Papa.unparse(template);
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    saveAs(blob, 'modele_import.csv');
  }

  resetProcess() {
    this.file = null;
    this.previewData = null;
    this.importResult = null;
    this.errorMessage = '';
    this.stepper.reset();
  }
}
