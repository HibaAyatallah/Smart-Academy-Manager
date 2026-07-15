import { ComponentFixture, TestBed } from '@angular/core/testing';
import { PageHeaderComponent } from './page-header.component';

describe('PageHeaderComponent', () => {
  let fixture: ComponentFixture<PageHeaderComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [PageHeaderComponent] }).compileComponents();
    fixture = TestBed.createComponent(PageHeaderComponent);
  });

  it('renders a semantic title and optional description', () => {
    fixture.componentRef.setInput('title', 'Candidatures');
    fixture.componentRef.setInput('subtitle', 'Suivi des dossiers');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('h1').textContent).toContain('Candidatures');
    expect(fixture.nativeElement.querySelector('p').textContent).toContain('Suivi des dossiers');
  });
});
