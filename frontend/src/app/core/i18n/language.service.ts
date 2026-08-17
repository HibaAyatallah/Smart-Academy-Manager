import { DOCUMENT } from '@angular/common';
import { Injectable, inject } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { AppLanguage, SUPPORTED_LANGUAGES, TRANSLATIONS, TranslationParams } from './translations';

@Injectable({providedIn:'root'})
export class LanguageService {
  private readonly document = inject(DOCUMENT);
  private readonly storageKey = 'preferred_language';
  private readonly legacyStorageKey = 'smart-academy-language';
  private readonly subject = new BehaviorSubject<AppLanguage>(this.restore());
  readonly language$ = this.subject.asObservable();
  constructor() { this.apply(this.subject.value); }
  get current(): AppLanguage { return this.subject.value; }
  get locale(): string { return ({fr: 'fr-FR', en: 'en-US'} satisfies Record<AppLanguage, string>)[this.current]; }
  initializeFromProfile(language?: string): void {
    // The server profile is authoritative. Browser storage only provides the
    // initial language while /auth/me/ is loading.
    if (this.isSupported(language)) this.setLanguage(language);
  }
  translate(key: string, params: TranslationParams = {}): string {
    const template = TRANSLATIONS[this.current][key] ?? TRANSLATIONS.fr[key];
    if (!template) { console.warn(`[i18n] Missing translation key: ${key}`); return key; }
    return template.replace(/{{\s*([\w.]+)\s*}}/g, (_, name: string) => String(params[name] ?? `{{${name}}}`));
  }
  setLanguage(language: AppLanguage): void {
    if (!this.isSupported(language)) return;
    localStorage.setItem(this.storageKey, language);
    localStorage.removeItem(this.legacyStorageKey);
    if (language !== this.subject.value) this.subject.next(language);
    this.apply(language);
  }
  private restore(): AppLanguage {
    const stored = localStorage.getItem(this.storageKey) ?? localStorage.getItem(this.legacyStorageKey);
    const language: AppLanguage = stored === 'en' ? 'en' : 'fr';
    if (stored) localStorage.setItem(this.storageKey, language);
    localStorage.removeItem(this.legacyStorageKey);
    return language;
  }
  private isSupported(language?: string | null): language is AppLanguage {
    return SUPPORTED_LANGUAGES.includes(language as AppLanguage);
  }
  private apply(language: AppLanguage): void { this.document.documentElement.lang=language; this.document.documentElement.dir='ltr'; this.document.body.classList.remove('rtl'); }
}
