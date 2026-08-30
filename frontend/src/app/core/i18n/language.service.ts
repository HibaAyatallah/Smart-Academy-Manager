import { DOCUMENT } from '@angular/common';
import { Injectable, inject } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { AppLanguage, TRANSLATIONS, TranslationParams } from './translations';

@Injectable({providedIn:'root'})
export class LanguageService {
  private readonly document = inject(DOCUMENT);
  private readonly storageKey = 'preferred_language';
  private readonly legacyStorageKey = 'smart-academy-language';
  private readonly subject = new BehaviorSubject<AppLanguage>('fr');
  readonly language$ = this.subject.asObservable();
  constructor() { this.setLanguage('fr'); }
  get current(): AppLanguage { return this.subject.value; }
  get locale(): string { return 'fr-FR'; }
  initializeFromProfile(_language?: string): void { this.setLanguage('fr'); }
  translate(key: string, params: TranslationParams = {}): string {
    const template = TRANSLATIONS[this.current][key] ?? TRANSLATIONS.fr[key];
    if (!template) { console.warn(`[i18n] Missing translation key: ${key}`); return key; }
    return template.replace(/{{\s*([\w.]+)\s*}}/g, (_, name: string) => String(params[name] ?? `{{${name}}}`));
  }
  setLanguage(_language: AppLanguage): void {
    localStorage.setItem(this.storageKey, 'fr');
    localStorage.removeItem(this.legacyStorageKey);
    if (this.subject.value !== 'fr') this.subject.next('fr');
    this.apply('fr');
  }
  private apply(language: AppLanguage): void { this.document.documentElement.lang=language; this.document.documentElement.dir='ltr'; this.document.body.classList.remove('rtl'); }
}
