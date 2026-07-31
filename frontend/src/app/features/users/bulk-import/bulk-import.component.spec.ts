import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BulkImportComponent } from './bulk-import.component';
import { UserImportService } from '../../../core/services/user-import.service';
import { of, throwError } from 'rxjs';
import { HttpClientTestingModule } from '@angular/common/http/testing';

describe('BulkImportComponent', () => {
  let component: BulkImportComponent;
  let fixture: ComponentFixture<BulkImportComponent>;
  let userImportService: jasmine.SpyObj<UserImportService>;

  beforeEach(async () => {
    const spy = jasmine.createSpyObj('UserImportService', ['previewImport', 'confirmImport']);
    
    await TestBed.configureTestingModule({
      imports: [BulkImportComponent, HttpClientTestingModule],
      providers: [
        { provide: UserImportService, useValue: spy }
      ]
    }).compileComponents();

    userImportService = TestBed.inject(UserImportService) as jasmine.SpyObj<UserImportService>;
    fixture = TestBed.createComponent(BulkImportComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should upload file and show preview', () => {
    const mockFile = new File([''], 'test.csv', { type: 'text/csv' });
    component.file = mockFile;
    
    userImportService.previewImport.and.returnValue(of({
      valid_count: 1,
      invalid_count: 0,
      skipped_count: 0,
      valid_rows: [{ row: 2, payload: { first_name: 'Test' } }],
      invalid_rows: [],
      skipped_rows: []
    }));

    component.uploadFile();
    expect(userImportService.previewImport).toHaveBeenCalledWith(mockFile);
    expect(component.previewData?.valid_count).toBe(1);
    expect(component.activeTab).toBe('valid');
  });

  it('should handle validation errors', () => {
    const mockFile = new File([''], 'test.csv', { type: 'text/csv' });
    component.file = mockFile;
    
    userImportService.previewImport.and.returnValue(of({
      valid_count: 0,
      invalid_count: 1,
      skipped_count: 0,
      valid_rows: [],
      invalid_rows: [{ row: 2, errors: ['Error 1'] }],
      skipped_rows: []
    }));

    component.uploadFile();
    expect(component.previewData?.invalid_count).toBe(1);
    expect(component.activeTab).toBe('invalid');
  });

  it('should confirm import and show results', () => {
    spyOn(window, 'confirm').and.returnValue(true);
    component.previewData = {
      valid_count: 1, invalid_count: 0, skipped_count: 0,
      valid_rows: [{}], invalid_rows: [], skipped_rows: []
    };

    userImportService.confirmImport.and.returnValue(of({
      results: [{ first_name: 'Test', professional_email: 'test@finatech.com', temporary_password: 'pwd' }]
    }));

    component.confirmImport();
    expect(userImportService.confirmImport).toHaveBeenCalled();
    expect(component.importResult?.results?.length).toBe(1);
  });
});
