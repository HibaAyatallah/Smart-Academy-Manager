import { ComponentFixture, TestBed } from '@angular/core/testing';
import { EmptyStateComponent } from './empty-state.component';

describe('EmptyStateComponent', () => {
  let fixture: ComponentFixture<EmptyStateComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({ imports: [EmptyStateComponent] }).compileComponents();
    fixture = TestBed.createComponent(EmptyStateComponent);
  });

  it('renders an accessible honest empty state', () => {
    fixture.componentRef.setInput('title', 'Aucune donnée');
    fixture.componentRef.setInput('message', 'Aucune action en attente.');
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[role="status"]')).toBeTruthy();
    expect(fixture.nativeElement.textContent).toContain('Aucune action en attente.');
  });
});
