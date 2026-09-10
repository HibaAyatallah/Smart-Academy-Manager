import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { provideNoopAnimations } from '@angular/platform-browser/animations';

import { PublicLayoutComponent } from './public-layout.component';

@Component({ standalone: true, template: '<h1>Catalogue public des offres</h1>' })
class PublicOffersTestPage {}

describe('PublicLayoutComponent', () => {
  let fixture: ComponentFixture<PublicLayoutComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PublicLayoutComponent],
      providers: [
        provideNoopAnimations(),
        provideRouter([{ path: 'offres', component: PublicOffersTestPage }]),
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(PublicLayoutComponent);
    fixture.detectChanges();
  });

  it('renders Offres as a translated Angular link and navigates to the public catalogue', async () => {
    const link = fixture.nativeElement.querySelector('.desktop-nav a[href="/offres"]') as HTMLAnchorElement | null;
    expect(link).not.toBeNull();
    expect(link?.textContent?.trim()).toBe('Offres');

    link?.click();
    await fixture.whenStable();
    fixture.detectChanges();

    expect(TestBed.inject(Router).url).toBe('/offres');
    expect(fixture.nativeElement.textContent).toContain('Catalogue public des offres');
  });
});
