import {TestBed} from '@angular/core/testing';
import {LanguageService} from './language.service';
import {TRANSLATIONS} from './translations';

describe('LanguageService',()=>{
  beforeEach(()=>{localStorage.clear();document.documentElement.lang='fr';TestBed.configureTestingModule({});});
  afterEach(()=>localStorage.clear());
  it('defaults to French and persists English with the canonical key',()=>{
    const service=TestBed.inject(LanguageService);
    expect(service.current).toBe('fr');
    service.setLanguage('en');
    expect(localStorage.getItem('preferred_language')).toBe('en');
    expect(document.documentElement.lang).toBe('en');
    expect(service.translate('common.save')).toBe('Save');
  });
  it('uses the backend profile as the authority over stale browser storage',()=>{
    const service=TestBed.inject(LanguageService);
    service.setLanguage('fr');
    service.initializeFromProfile('en');
    expect(service.current).toBe('en');
    expect(localStorage.getItem('preferred_language')).toBe('en');
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
  });
});
