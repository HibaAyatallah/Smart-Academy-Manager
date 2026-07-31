import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { PaginatedResponse } from '../models/application.models';
import { HRBusinessUnitGroup, HRInternProfile, InternDocument, InternDocumentRequirement, InternEvaluation, InternProfile } from '../models/internship.models';

@Injectable({ providedIn: 'root' })
export class InternshipService {
  private readonly http = inject(HttpClient); private readonly base = environment.apiBaseUrl;
  private params(values: Record<string, unknown> = {}) { let p = new HttpParams(); Object.entries(values).forEach(([k,v]) => { if(v!==''&&v!==null&&v!==undefined)p=p.set(k,String(v)); }); return p; }
  getInterns(filters: Record<string, unknown> = {}): Observable<PaginatedResponse<InternProfile>> { return this.http.get<PaginatedResponse<InternProfile>>(`${this.base}interns/`, { params: this.params(filters) }); }
  getIntern(id: number): Observable<InternProfile> { return this.http.get<InternProfile>(`${this.base}interns/${id}/`); }
  downloadSpecification(id:number):Observable<Blob>{return this.http.get(`${this.base}interns/${id}/specification/`,{responseType:'blob'});}
  updateIntern(id: number, data: Partial<InternProfile>): Observable<InternProfile> { return this.http.patch<InternProfile>(`${this.base}interns/${id}/`, data); }
  getHRGroups(): Observable<HRBusinessUnitGroup[]> { return this.http.get<HRBusinessUnitGroup[]>(`${this.base}hr/collaborators/`); }
  getHRInterns(): Observable<PaginatedResponse<HRInternProfile>> { return this.http.get<PaginatedResponse<HRInternProfile>>(`${this.base}hr/interns/`); }
  getHRIntern(id: number): Observable<HRInternProfile> { return this.http.get<HRInternProfile>(`${this.base}hr/interns/${id}/`); }
  uploadDocument(intern: number, requirement: number, file: File): Observable<InternDocument> { const body = new FormData(); body.append('intern', String(intern)); body.append('requirement', String(requirement)); body.append('file', file); return this.http.post<InternDocument>(`${this.base}intern-documents/`, body); }
  downloadDocument(id: number): Observable<Blob> { return this.http.get(`${this.base}intern-documents/${id}/download/`, { responseType: 'blob' }); }
  validateDocument(id: number, comment = ''): Observable<InternDocument> { return this.http.post<InternDocument>(`${this.base}intern-documents/${id}/validate/`, { comment }); }
  rejectDocument(id:number,comment:string):Observable<InternDocument>{return this.http.post<InternDocument>(`${this.base}intern-documents/${id}/reject/`,{comment});}
  getRequirements():Observable<PaginatedResponse<InternDocumentRequirement>>{return this.http.get<PaginatedResponse<InternDocumentRequirement>>(`${this.base}intern-document-requirements/`);}
  createRequirement(data:Partial<InternDocumentRequirement>):Observable<InternDocumentRequirement>{return this.http.post<InternDocumentRequirement>(`${this.base}intern-document-requirements/`,data);}
  createEvaluation(data: Record<string, unknown>): Observable<InternEvaluation> { return this.http.post<InternEvaluation>(`${this.base}intern-evaluations/`, data); }
}
