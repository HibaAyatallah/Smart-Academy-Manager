import {ChangeDetectorRef, OnDestroy, Pipe, PipeTransform, inject} from '@angular/core';
import {Subscription} from 'rxjs';
import {LanguageService} from './language.service';

@Pipe({name:'localizedDate',standalone:true,pure:false})
export class LocalizedDatePipe implements PipeTransform, OnDestroy {
  private readonly language=inject(LanguageService);
  private readonly cdr=inject(ChangeDetectorRef);
  private readonly subscription:Subscription;
  constructor(){this.subscription=this.language.language$.subscribe(()=>this.cdr.markForCheck());}
  transform(value:string|number|Date|null|undefined, format='mediumDate'):string {
    if(value===null||value===undefined||value==='') return '';
    const date=value instanceof Date?value:new Date(value);
    if(Number.isNaN(date.getTime())) return '';
    const options:Intl.DateTimeFormatOptions = format==='short'
      ? {dateStyle:'short',timeStyle:'short'}
      : format==='shortDate'
        ? {dateStyle:'short'}
        : {dateStyle:'medium'};
    return new Intl.DateTimeFormat(this.language.locale,options).format(date);
  }
  ngOnDestroy(){this.subscription.unsubscribe();}
}
