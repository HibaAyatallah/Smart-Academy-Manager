import { HttpClient, HttpHeaders } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { map, Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AppLanguage } from '../i18n/translations';

export interface AnswerSource { type:string; name:string; reference:string; id:number|null; url:string; }
export interface ChatMessage { id: number; role: 'USER' | 'ASSISTANT'; content: string; sources?:AnswerSource[]; request_id?:string; created_at: string; }
export interface Conversation { id: number; language: AppLanguage; messages: ChatMessage[]; created_at: string; updated_at: string; }
export interface ChatbotHealth { backend: boolean; ollama: boolean; model: string; model_available: boolean; error_code: string | null; streaming_supported: boolean; }

@Injectable({ providedIn: 'root' })
export class AssistantService {
  private readonly http = inject(HttpClient);
  private readonly conversationBase = `${environment.apiBaseUrl}assistant/conversations/`;
  private readonly chatbotBase = `${environment.apiBaseUrl}chatbot/`;

  lastServerTiming = '';
  private readonly jsonHeaders = new HttpHeaders({
    Accept: 'application/json',
    'Content-Type': 'application/json',
  });

  ask(message: string, language: AppLanguage, conversation_id?: number): Observable<Conversation> {
    return this.http.post<Conversation>(`${this.chatbotBase}messages/`, { message, language, conversation_id, request_id:crypto.randomUUID() }, {headers:this.jsonHeaders,observe:'response'}).pipe(
      map(response => {
        this.lastServerTiming = response.headers.get('Server-Timing') ?? '';
        if (!response.body) throw new Error('Empty chatbot response');
        return response.body;
      })
    );
  }
  stream(message:string,language:AppLanguage,request_id:string,conversation_id?:number,signal?:AbortSignal):Observable<{event:string;data:any}>{
    return new Observable(observer=>{
      if(signal?.aborted){observer.complete();return;}
      const subscription=this.http.post<Conversation>(`${this.chatbotBase}messages/`,
        {message,language,request_id,conversation_id},
        {headers:this.jsonHeaders},
      ).subscribe({
        next:conversation=>{
          observer.next({event:'meta',data:{conversation_id:conversation.id,request_id}});
          const answer=conversation.messages.find(item=>item.role==='ASSISTANT'&&item.request_id===request_id);
          if(!answer){observer.error(new Error('Chatbot response does not match the request'));return;}
          observer.next({event:'done',data:{request_id,message:answer}});
          observer.complete();
        },
        error:error=>observer.error(error?.error??error),
      });
      const abort=()=>{subscription.unsubscribe();observer.complete();};
      signal?.addEventListener('abort',abort,{once:true});
      return()=>{signal?.removeEventListener('abort',abort);subscription.unsubscribe();};
    });
  }
  health(): Observable<ChatbotHealth> { return this.http.get<ChatbotHealth>(`${this.chatbotBase}health/`); }
  suggestions(): Observable<{ suggestions: string[] }> { return this.http.get<{ suggestions: string[] }>(`${this.conversationBase}suggestions/`); }
  list(): Observable<{ results?: Conversation[] } | Conversation[]> { return this.http.get<{ results?: Conversation[] } | Conversation[]>(this.conversationBase); }
  delete(id: number): Observable<void> { return this.http.delete<void>(`${this.conversationBase}${id}/`); }
}
