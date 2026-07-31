import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { environment } from '../../../environments/environment';
import { ReportData, HRDashboardData } from '../models/report.models';

@Injectable({ providedIn: 'root' })
export class ReportService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  private params(values: Record<string, unknown>) {
    let p = new HttpParams();
    Object.entries(values).forEach(([k, v]) => {
      if (v !== '' && v !== null && v !== undefined) p = p.set(k, String(v));
    });
    return p;
  }

  summary(filters: Record<string, unknown>) {
    return this.http.get<ReportData>(`${this.base}reports/summary/`, {
      params: this.params(filters),
    });
  }

  hrDashboard() {
    return this.http.get<HRDashboardData>(`${this.base}reports/hr-dashboard/`);
  }

  export(format: 'csv' | 'pdf', filters: Record<string, unknown>) {
    return this.http.get(`${this.base}reports/export/${format}/`, {
      params: this.params(filters),
      responseType: 'blob',
    });
  }
}
