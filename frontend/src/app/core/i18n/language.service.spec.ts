import {TestBed} from '@angular/core/testing';
import {LanguageService} from './language.service';
import {TRANSLATIONS} from './translations';

describe('LanguageService',()=>{
  beforeEach(()=>{localStorage.clear();document.documentElement.lang='fr';TestBed.configureTestingModule({});});
  afterEach(()=>localStorage.clear());
  it('locks the application to French even when English is requested',()=>{
    const service=TestBed.inject(LanguageService);
    expect(service.current).toBe('fr');
    service.setLanguage('en');
    expect(service.current).toBe('fr');
    expect(localStorage.getItem('preferred_language')).toBe('fr');
    expect(document.documentElement.lang).toBe('fr');
    expect(service.translate('common.save')).toBe('Enregistrer');
    expect(service.translate('public.offers')).toBe('Offres');
  });
  it('ignores an English profile preference and removes stale language storage',()=>{
    localStorage.setItem('smart-academy-language','en');
    const service=TestBed.inject(LanguageService);
    service.initializeFromProfile('en');
    expect(service.current).toBe('fr');
    expect(localStorage.getItem('preferred_language')).toBe('fr');
    expect(localStorage.getItem('smart-academy-language')).toBeNull();
  });
  it('replaces a stored English preference with French at startup',()=>{
    localStorage.setItem('preferred_language','en');
    const service=TestBed.inject(LanguageService);
    expect(service.current).toBe('fr');
    expect(localStorage.getItem('preferred_language')).toBe('fr');
  });
  it('interpolates dynamic values and falls back to French',()=>{
    const service=TestBed.inject(LanguageService);
    expect(service.translate('dashboard.greeting',{name:'Hiba'})).toBe('Bonjour Hiba');
    expect(service.translate('missing.key')).toBe('missing.key');
  });
  it('keeps the French and English catalogs in exact parity',()=>{
    expect(Object.keys(TRANSLATIONS.fr).sort()).toEqual(Object.keys(TRANSLATIONS.en).sort());
    expect(Object.values(TRANSLATIONS.fr).every(Boolean)).toBeTrue();
    expect(Object.values(TRANSLATIONS.en).every(Boolean)).toBeTrue();
    expect(TRANSLATIONS.en['public.offers']).toBe('Offers');
  });
});
