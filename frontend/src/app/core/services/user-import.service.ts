import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface ImportPreviewResult {
  valid_count: number;
  invalid_count: number;
  skipped_count: number;
  valid_rows: any[];
  invalid_rows: any[];
  skipped_rows: any[];
  missing_bus?: string[];
  error?: string;
}

export interface ImportConfirmResult {
  results?: any[];
  error?: string;
}

@Injectable({
  providedIn: 'root'
})
export class UserImportService {
  private apiUrl = `${environment.apiBaseUrl}import/`;

  constructor(private http: HttpClient) {}

  previewImport(file: File): Observable<ImportPreviewResult> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<ImportPreviewResult>(`${this.apiUrl}preview/`, formData);
  }

  confirmImport(validRows: any[], createMissingBus: boolean = false): Observable<ImportConfirmResult> {
    return this.http.post<ImportConfirmResult>(`${this.apiUrl}confirm/`, { 
      valid_rows: validRows,
      create_missing_bus: createMissingBus
    });
  }
}
