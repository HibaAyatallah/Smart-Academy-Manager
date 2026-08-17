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
import { MatSnackBar } from '@angular/material/snack-bar';

@Component({
  selector: 'app-bulk-import',
  standalone: true,
  imports: [
    CommonModule,
    MatStepperModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatTooltipModule
  ],
  templateUrl: './bulk-import.component.html',
  styleUrls: ['./bulk-import.component.scss']
})
export class BulkImportComponent {
  @ViewChild('stepper') stepper!: MatStepper;

  file: File | null = null;
  previewData: ImportPreviewResult | null = null;
  importResult: ImportConfirmResult | null = null;
  isLoading = false;
  isConfirming = false;
  errorMessage = '';
  activeTab: 'valid' | 'invalid' | 'skipped' = 'valid';

  get stats() {
    let collaborateurs = 0;
    let formateurs = 0;
    let clientsExternes = 0;
    let stagiaires = 0;

    if (this.previewData && this.previewData.valid_rows) {
      this.previewData.valid_rows.forEach(row => {
        const role = row.payload?.role;
        switch (role) {
          case 'EMPLOYEE':
          case 'BU_MANAGER':
            collaborateurs++;
            break;
          case 'TRAINER_TUTOR':
            formateurs++;
            break;
          case 'CLIENT':
            clientsExternes++;
            break;
          case 'INTERN':
            stagiaires++;
            break;
        }
      });
    }

    return {
      collaborateurs,
      formateurs,
      clientsExternes,
      stagiaires,
      total: this.previewData?.valid_count || 0
    };
  }

  constructor(
    private userImportService: UserImportService,
    private snackBar: MatSnackBar
  ) {}

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

        if (this.previewData.valid_count > 0) {
          this.activeTab = 'valid';
        } else if (this.previewData.invalid_count > 0) {
          this.activeTab = 'invalid';
        }
        // Advance to step 2 (preview)
        setTimeout(() => this.stepper.next(), 100);
      },
      error: (err: HttpErrorResponse) => {
        this.isLoading = false;
        const msg = err.error?.error || err.message || 'Erreur système inconnue.';
        this.errorMessage = msg;
        this.snackBar.open(`Erreur d'analyse : ${msg}`, 'Fermer', { duration: 6000, panelClass: ['snack-error'] });
      }
    });
  }

  /**
   * Passe de l'étape Prévisualisation (étape 2) à l'étape Confirmation (étape 3).
   * Vérifie les préconditions avant d'avancer le stepper.
   */
  goToConfirmation() {
    if (!this.previewData) {
      const msg = 'Aucune donnée de prévisualisation disponible. Veuillez analyser un fichier d\'abord.';
      this.errorMessage = msg;
      this.snackBar.open(msg, 'Fermer', { duration: 5000, panelClass: ['snack-error'] });
      return;
    }

    if (this.previewData.valid_count === 0) {
      const msg = 'Impossible de continuer : aucune ligne valide à importer.';
      this.errorMessage = msg;
      this.snackBar.open(msg, 'Fermer', { duration: 5000, panelClass: ['snack-error'] });
      return;
    }

    this.errorMessage = '';
    this.stepper.next();
  }

  confirmImport() {
    // Protection double-clic
    if (this.isConfirming || this.isLoading) return;

    if (!this.previewData || this.previewData.valid_rows.length === 0) {
      const msg = 'Aucune donnée valide à importer.';
      this.errorMessage = msg;
      this.snackBar.open(msg, 'Fermer', { duration: 5000, panelClass: ['snack-error'] });
      return;
    }

    this.isLoading = true;
    this.isConfirming = true;
    this.errorMessage = '';

    this.userImportService.confirmImport(this.previewData.valid_rows).subscribe({
      next: (res) => {
        this.isLoading = false;
        this.isConfirming = false;
        this.importResult = res;
        // Advance to step 4 (result)
        setTimeout(() => this.stepper.next(), 100);
      },
      error: (err: HttpErrorResponse) => {
        this.isLoading = false;
        this.isConfirming = false;
        const msg = err.error?.error || "Erreur lors de l'importation.";
        this.errorMessage = msg;
        this.snackBar.open(`Erreur d'importation : ${msg}`, 'Fermer', { duration: 8000, panelClass: ['snack-error'] });
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
    this.isConfirming = false;
    this.stepper.reset();
  }
}
