import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { PaginatedResponse } from '../models/application.models';
import { ClientTraining, SessionAttendance, Training, TrainingCertificate, TrainingEnrollment, TrainingSession } from '../models/training.models';

@Injectable({ providedIn: 'root' })
export class TrainingService {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = environment.apiBaseUrl;

  private params(values: Record<string, unknown> = {}): HttpParams {
    let params = new HttpParams();
    Object.entries(values).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) params = params.set(key, String(value));
    });
    return params;
  }

  getTrainings(filters: Record<string, unknown> = {}): Observable<PaginatedResponse<Training>> {
    return this.http.get<PaginatedResponse<Training>>(`${this.baseUrl}trainings/`, { params: this.params(filters) });
  }
  getTraining(id: number): Observable<Training> { return this.http.get<Training>(`${this.baseUrl}trainings/${id}/`); }
  createTraining(data: Partial<Training>): Observable<Training> { return this.http.post<Training>(`${this.baseUrl}trainings/`, data); }
  updateTraining(id: number, data: Partial<Training>): Observable<Training> { return this.http.patch<Training>(`${this.baseUrl}trainings/${id}/`, data); }
  deleteTraining(id: number): Observable<void> { return this.http.delete<void>(`${this.baseUrl}trainings/${id}/`); }
  trainingAction(id: number, action: 'publish' | 'archive'): Observable<unknown> { return this.http.post(`${this.baseUrl}trainings/${id}/${action}/`, {}); }

  getSessions(filters: Record<string, unknown> = {}): Observable<PaginatedResponse<TrainingSession>> { return this.http.get<PaginatedResponse<TrainingSession>>(`${this.baseUrl}training-sessions/`, { params: this.params(filters) }); }
  createSession(data: Partial<TrainingSession>): Observable<TrainingSession> { return this.http.post<TrainingSession>(`${this.baseUrl}training-sessions/`, data); }
  updateSession(id: number, data: Partial<TrainingSession>): Observable<TrainingSession> { return this.http.patch<TrainingSession>(`${this.baseUrl}training-sessions/${id}/`, data); }
  sessionAction(id: number, action: 'open_registration' | 'close_registration' | 'cancel' | 'complete'): Observable<unknown> { return this.http.post(`${this.baseUrl}training-sessions/${id}/${action}/`, {}); }

  requestEnrollment(training: number, session: number): Observable<TrainingEnrollment> { return this.http.post<TrainingEnrollment>(`${this.baseUrl}enrollments/`, { training, session }); }
  getEnrollments(filters: Record<string, unknown> = {}): Observable<PaginatedResponse<TrainingEnrollment>> { return this.http.get<PaginatedResponse<TrainingEnrollment>>(`${this.baseUrl}enrollments/`, { params: this.params(filters) }); }
  decideEnrollment(id: number, action: 'manager_approve' | 'manager_reject' | 'super_admin_approve' | 'super_admin_reject', comment = ''): Observable<TrainingEnrollment> { return this.http.post<TrainingEnrollment>(`${this.baseUrl}enrollments/${id}/${action}/`, { approved: action.endsWith('approve'), comment }); }
  enrollmentAction(id: number, action: 'cancel' | 'complete'): Observable<TrainingEnrollment> { return this.http.post<TrainingEnrollment>(`${this.baseUrl}enrollments/${id}/${action}/`, {}); }
  directEnrollment(user: number, training: number, session: number): Observable<TrainingEnrollment> { return this.http.post<TrainingEnrollment>(`${this.baseUrl}enrollments/direct_enrollment/`, { user, training, session }); }

  getClientTrainings(): Observable<PaginatedResponse<ClientTraining>> { return this.http.get<PaginatedResponse<ClientTraining>>(`${this.baseUrl}client/trainings/`); }
  getAttendance(filters: Record<string, unknown> = {}): Observable<PaginatedResponse<SessionAttendance>> { return this.http.get<PaginatedResponse<SessionAttendance>>(`${this.baseUrl}attendance/`, { params: this.params(filters) }); }
  recordAttendance(enrollment:number, status:string, note=''): Observable<SessionAttendance> { return this.http.post<SessionAttendance>(`${this.baseUrl}attendance/`, { enrollment, status, note }); }
  updateAttendance(id:number, status:string, note=''): Observable<SessionAttendance> { return this.http.patch<SessionAttendance>(`${this.baseUrl}attendance/${id}/`, { status, note }); }
  validateAttendance(id:number): Observable<SessionAttendance> { return this.http.post<SessionAttendance>(`${this.baseUrl}attendance/${id}/validate/`, {}); }
  getCertificates(filters: Record<string, unknown> = {}): Observable<PaginatedResponse<TrainingCertificate>> { return this.http.get<PaginatedResponse<TrainingCertificate>>(`${this.baseUrl}certificates/`, { params: this.params(filters) }); }
  downloadCertificate(id:number): Observable<Blob> { return this.http.get(`${this.baseUrl}certificates/${id}/download/`, { responseType:'blob' }); }
}
