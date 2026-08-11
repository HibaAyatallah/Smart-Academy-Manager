import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { BulkImportComponent } from './bulk-import.component';
import { UserImportService } from '../../../core/services/user-import.service';
import { MatSnackBar } from '@angular/material/snack-bar';
import { of, throwError } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { ImportPreviewResult } from '../../../core/services/user-import.service';
import { HttpErrorResponse } from '@angular/common/http';

/** Données de prévisualisation valides (29 lignes simulées par 2) */
const mockPreviewResult: ImportPreviewResult = {
  valid_count: 2,
  invalid_count: 0,
  skipped_count: 0,
  valid_rows: [
    { row: 2, payload: { first_name: 'Alice', last_name: 'Martin', contact_email: 'alice@test.com', role: 'EMPLOYEE', business_unit_name: 'NetSEC' } },
    { row: 3, payload: { first_name: 'Bob',   last_name: 'Dupont', contact_email: 'bob@test.com',   role: 'INTERN',   business_unit_name: null } }
  ],
  invalid_rows: [],
  skipped_rows: []
};

const mockPreviewWithInvalid: ImportPreviewResult = {
  valid_count: 1,
  invalid_count: 1,
  skipped_count: 0,
  valid_rows: [{ row: 2, payload: { role: 'EMPLOYEE' } }],
  invalid_rows: [{ row: 3, errors: ['Email invalide'] }],
  skipped_rows: []
};

const mockPreviewEmpty: ImportPreviewResult = {
  valid_count: 0,
  invalid_count: 0,
  skipped_count: 0,
  valid_rows: [],
  invalid_rows: [],
  skipped_rows: []
};

describe('BulkImportComponent', () => {
  let component: BulkImportComponent;
  let fixture: ComponentFixture<BulkImportComponent>;
  let userImportService: jasmine.SpyObj<UserImportService>;
  let snackBar: jasmine.SpyObj<MatSnackBar>;

  beforeEach(async () => {
    const serviceSpy = jasmine.createSpyObj('UserImportService', ['previewImport', 'confirmImport']);
    const snackBarSpy = jasmine.createSpyObj('MatSnackBar', ['open']);

    await TestBed.configureTestingModule({
      imports: [BulkImportComponent, HttpClientTestingModule, NoopAnimationsModule],
      providers: [
        { provide: UserImportService, useValue: serviceSpy },
        { provide: MatSnackBar, useValue: snackBarSpy }
      ]
    }).compileComponents();

    userImportService = TestBed.inject(UserImportService) as jasmine.SpyObj<UserImportService>;
    snackBar = TestBed.inject(MatSnackBar) as jasmine.SpyObj<MatSnackBar>;
    fixture = TestBed.createComponent(BulkImportComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  // ─── Initialisation ────────────────────────────────────────────────────────

  it('devrait créer le composant', () => {
    expect(component).toBeTruthy();
  });

  it('devrait initialiser toutes les propriétés à leurs valeurs par défaut', () => {
    expect(component.file).toBeNull();
    expect(component.previewData).toBeNull();
    expect(component.importResult).toBeNull();
    expect(component.isLoading).toBeFalse();
    expect(component.isConfirming).toBeFalse();
    expect(component.errorMessage).toBe('');
    expect(component.activeTab).toBe('valid');
  });

  // ─── Sélection du fichier ──────────────────────────────────────────────────

  it('devrait sélectionner un fichier via onFileSelected()', () => {
    const mockFile = new File([''], 'test.csv', { type: 'text/csv' });
    component.onFileSelected({ target: { files: [mockFile] } });
    expect(component.file).toBe(mockFile);
    expect(component.errorMessage).toBe('');
  });

  it('devrait sélectionner un fichier via onDrop()', () => {
    const mockFile = new File([''], 'test.csv', { type: 'text/csv' });
    const mockEvent = { preventDefault: () => {}, dataTransfer: { files: [mockFile] } };
    component.onDrop(mockEvent);
    expect(component.file).toBe(mockFile);
  });

  // ─── Analyse du fichier ────────────────────────────────────────────────────

  it('devrait analyser le fichier et afficher la prévisualisation', fakeAsync(() => {
    const mockFile = new File([''], 'test.csv', { type: 'text/csv' });
    component.file = mockFile;
    userImportService.previewImport.and.returnValue(of(mockPreviewResult));

    const stepperSpy = spyOn(component.stepper, 'next');
    component.uploadFile();
    tick(200);

    expect(userImportService.previewImport).toHaveBeenCalledWith(mockFile);
    expect(component.previewData).toEqual(mockPreviewResult);
    expect(component.previewData?.valid_count).toBe(2);
    expect(component.activeTab).toBe('valid');
    expect(component.isLoading).toBeFalse();
    expect(stepperSpy).toHaveBeenCalled();
  }));

  it('devrait afficher l\'onglet invalides si valid_count = 0', fakeAsync(() => {
    component.file = new File([''], 'test.csv');
    userImportService.previewImport.and.returnValue(of({
      ...mockPreviewEmpty,
      invalid_count: 1,
      invalid_rows: [{ row: 2, errors: ['Erreur'] }]
    }));
    spyOn(component.stepper, 'next');
    component.uploadFile();
    tick(200);
    expect(component.activeTab).toBe('invalid');
  }));

  it('devrait gérer une erreur d\'analyse et afficher le Snackbar', () => {
    component.file = new File([''], 'test.csv');
    const err = new HttpErrorResponse({ error: { error: 'Fichier corrompu' }, status: 400 });
    userImportService.previewImport.and.returnValue(throwError(() => err));

    component.uploadFile();

    expect(component.isLoading).toBeFalse();
    expect(component.errorMessage).toBe('Fichier corrompu');
    expect(snackBar.open).toHaveBeenCalledWith(
      jasmine.stringContaining('Fichier corrompu'), 'Fermer', jasmine.any(Object)
    );
  });

  // ─── goToConfirmation ──────────────────────────────────────────────────────

  it('devrait passer à la Confirmation quand valid_count > 0', () => {
    component.previewData = mockPreviewResult;
    const stepperSpy = spyOn(component.stepper, 'next');

    component.goToConfirmation();

    expect(stepperSpy).toHaveBeenCalledOnceWith();
    expect(component.errorMessage).toBe('');
  });

  it('devrait bloquer la navigation si previewData est null', () => {
    component.previewData = null;
    const stepperSpy = spyOn(component.stepper, 'next');

    component.goToConfirmation();

    expect(stepperSpy).not.toHaveBeenCalled();
    expect(component.errorMessage).not.toBe('');
    expect(snackBar.open).toHaveBeenCalled();
  });

  it('devrait bloquer la navigation si valid_count = 0', () => {
    component.previewData = mockPreviewEmpty;
    const stepperSpy = spyOn(component.stepper, 'next');

    component.goToConfirmation();

    expect(stepperSpy).not.toHaveBeenCalled();
    expect(component.errorMessage).toContain('aucune ligne valide');
    expect(snackBar.open).toHaveBeenCalled();
  });

  // ─── Stats ────────────────────────────────────────────────────────────────

  it('devrait calculer correctement les stats de rôles (1 EMPLOYEE + 1 INTERN)', () => {
    component.previewData = mockPreviewResult; // 1 EMPLOYEE + 1 INTERN
    const s = component.stats;
    expect(s.collaborateurs).toBe(1);
    expect(s.formateurs).toBe(0);
    expect(s.clientsExternes).toBe(0);
    expect(s.stagiaires).toBe(1);
    expect(s.total).toBe(2);
  });

  it('devrait calculer la répartition exacte : 20 collab / 1 client / 5 formateurs / 3 stagiaires', () => {
    const rows29: any[] = [
      // 20 collaborateurs
      ...Array.from({ length: 20 }, (_, i) => ({
        row: i + 2,
        payload: { role: 'EMPLOYEE', first_name: `C${i}`, last_name: 'N', contact_email: `c${i}@t.com`, business_unit_name: 'NetSEC' }
      })),
      // 1 client externe
      { row: 22, payload: { role: 'CLIENT', first_name: 'Cli', last_name: 'Ext', contact_email: 'cli@t.com', business_unit_name: null } },
      // 5 formateurs
      ...Array.from({ length: 5 }, (_, i) => ({
        row: i + 23,
        payload: { role: 'TRAINER_TUTOR', first_name: `F${i}`, last_name: 'N', contact_email: `f${i}@t.com`, business_unit_name: 'System' }
      })),
      // 3 stagiaires
      ...Array.from({ length: 3 }, (_, i) => ({
        row: i + 28,
        payload: { role: 'INTERN', first_name: `S${i}`, last_name: 'N', contact_email: `s${i}@t.com`, business_unit_name: 'Achat' }
      }))
    ];
    component.previewData = {
      valid_count: 29, invalid_count: 0, skipped_count: 0,
      valid_rows: rows29, invalid_rows: [], skipped_rows: []
    };
    const s = component.stats;
    expect(s.collaborateurs).toBe(20, '20 collaborateurs');
    expect(s.formateurs).toBe(5,    '5 formateurs');
    expect(s.clientsExternes).toBe(1, '1 client externe');
    expect(s.stagiaires).toBe(3,    '3 stagiaires');
    expect(s.total).toBe(29,        '29 total');
  });

  it('devrait retourner des stats à 0 si previewData est null', () => {
    component.previewData = null;
    const s = component.stats;
    expect(s.collaborateurs).toBe(0);
    expect(s.formateurs).toBe(0);
    expect(s.clientsExternes).toBe(0);
    expect(s.stagiaires).toBe(0);
    expect(s.total).toBe(0);
  });

  // ─── confirmImport ────────────────────────────────────────────────────────

  it('devrait confirmer l\'import et avancer au résultat', fakeAsync(() => {
    component.previewData = mockPreviewResult;
    const mockResult = { results: [{ first_name: 'Alice', professional_email: 'alice@finatech.com', temporary_password: 'Tmp123!' }] };
    userImportService.confirmImport.and.returnValue(of(mockResult));
    const stepperSpy = spyOn(component.stepper, 'next');

    component.confirmImport();
    tick(200);

    expect(userImportService.confirmImport).toHaveBeenCalledWith(mockPreviewResult.valid_rows);
    expect(component.importResult).toEqual(mockResult);
    expect(component.isLoading).toBeFalse();
    expect(component.isConfirming).toBeFalse();
    expect(stepperSpy).toHaveBeenCalled();
  }));

  it('devrait afficher une erreur Snackbar si le backend échoue', () => {
    component.previewData = mockPreviewResult;
    const err = new HttpErrorResponse({ error: { error: 'Quota dépassé' }, status: 503 });
    userImportService.confirmImport.and.returnValue(throwError(() => err));

    component.confirmImport();

    expect(component.isLoading).toBeFalse();
    expect(component.isConfirming).toBeFalse();
    expect(component.errorMessage).toBe('Quota dépassé');
    expect(snackBar.open).toHaveBeenCalledWith(
      jasmine.stringContaining('Quota dépassé'), 'Fermer', jasmine.any(Object)
    );
  });

  it('devrait ignorer un double-clic sur confirmImport()', () => {
    component.previewData = mockPreviewResult;
    component.isConfirming = true; // simule un clic déjà en cours

    component.confirmImport();

    expect(userImportService.confirmImport).not.toHaveBeenCalled();
  });

  it('devrait bloquer confirmImport() si aucune donnée valide', () => {
    component.previewData = mockPreviewEmpty;

    component.confirmImport();

    expect(userImportService.confirmImport).not.toHaveBeenCalled();
    expect(component.errorMessage).not.toBe('');
    expect(snackBar.open).toHaveBeenCalled();
  });

  // ─── resetProcess ─────────────────────────────────────────────────────────

  it('devrait réinitialiser le formulaire via resetProcess()', () => {
    component.previewData = mockPreviewResult;
    component.importResult = { results: [] };
    component.errorMessage = 'Une erreur';
    component.isConfirming = true;
    spyOn(component.stepper, 'reset');

    component.resetProcess();

    expect(component.file).toBeNull();
    expect(component.previewData).toBeNull();
    expect(component.importResult).toBeNull();
    expect(component.errorMessage).toBe('');
    expect(component.isConfirming).toBeFalse();
    expect(component.stepper.reset).toHaveBeenCalled();
  });
});
