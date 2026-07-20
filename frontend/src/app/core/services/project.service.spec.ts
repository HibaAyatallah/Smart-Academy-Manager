import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../environments/environment';
import { ProjectService } from './project.service';

describe('ProjectService', () => {
  let service: ProjectService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(ProjectService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('sends project list filters and assignments', () => {
    service.getProjects({ status: 'ACTIVE', search: 'portal', empty: '' }).subscribe();
    const list = http.expectOne((request) => request.url === `${environment.apiBaseUrl}projects/`);
    expect(list.request.params.get('status')).toBe('ACTIVE');
    expect(list.request.params.get('search')).toBe('portal');
    expect(list.request.params.has('empty')).toBeFalse();
    list.flush({ count: 0, next: null, previous: null, results: [] });

    service.createProject({ title: 'Portal', assignee_ids: [8, 9] }).subscribe();
    const create = http.expectOne(`${environment.apiBaseUrl}projects/`);
    expect(create.request.method).toBe('POST');
    expect(create.request.body.assignee_ids).toEqual([8, 9]);
    create.flush({});
  });

  it('supports deliverables, comments, uploads, and protected downloads', () => {
    service.updateDeliverable(4, { status: 'SUBMITTED' }).subscribe();
    const deliverable = http.expectOne(`${environment.apiBaseUrl}project-deliverables/4/`);
    expect(deliverable.request.method).toBe('PATCH');
    deliverable.flush({});

    service.addComment(2, 'Ready for review').subscribe();
    const comment = http.expectOne(`${environment.apiBaseUrl}project-comments/`);
    expect(comment.request.body).toEqual({ project: 2, content: 'Ready for review' });
    comment.flush({});

    service.uploadDocument(2, new File(['report'], 'report.txt')).subscribe();
    const upload = http.expectOne(`${environment.apiBaseUrl}project-documents/`);
    expect(upload.request.body instanceof FormData).toBeTrue();
    expect(upload.request.body.get('project')).toBe('2');
    upload.flush({});

    service.downloadDocument(7).subscribe();
    const download = http.expectOne(`${environment.apiBaseUrl}project-documents/7/download/`);
    expect(download.request.responseType).toBe('blob');
    download.flush(new Blob());
  });
});
