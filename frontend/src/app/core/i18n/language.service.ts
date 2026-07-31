import { DOCUMENT } from '@angular/common';
import { Injectable, inject } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { AppLanguage, TRANSLATIONS } from './translations';
@Injectable({providedIn:'root'})
export class LanguageService {
  private readonly document=inject(DOCUMENT); private readonly key='smart-academy-language';
  private readonly subject=new BehaviorSubject<AppLanguage>(this.restore()); readonly language$=this.subject.asObservable();
  constructor(){this.apply(this.subject.value);} get current(){return this.subject.value;}
  initializeFromProfile(language?: AppLanguage):void{if(!localStorage.getItem(this.key)&&language)this.setLanguage(language);}
  translate(key:string){return TRANSLATIONS[this.current][key]??TRANSLATIONS.fr[key]??key;}
  setLanguage(language:AppLanguage){if(!['fr','en','ar'].includes(language))return;localStorage.setItem(this.key,language);this.subject.next(language);this.apply(language);}
  private restore():AppLanguage{const value=localStorage.getItem(this.key);return value==='en'||value==='ar'?value:'fr';}
  private apply(language:AppLanguage){this.document.documentElement.lang=language;this.document.documentElement.dir=language==='ar'?'rtl':'ltr';this.document.body.classList.toggle('rtl',language==='ar');}
}
