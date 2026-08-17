import { DatePipe, NgFor, NgIf } from '@angular/common';
import { Component, ElementRef, ViewChild, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { finalize, forkJoin, Subscription } from 'rxjs';

import { AssistantService, ChatbotHealth, ChatMessage, Conversation } from '../../../core/services/assistant.service';
import { LanguageService } from '../../../core/i18n/language.service';
import { TranslatePipe } from '../../../core/i18n/translate.pipe';

@Component({selector:'app-chatbot',standalone:true,imports:[DatePipe,NgFor,NgIf,FormsModule,MatButtonModule,MatIconModule,MatProgressSpinnerModule,TranslatePipe,RouterLink],templateUrl:'./chatbot.component.html',styleUrl:'./chatbot.component.scss'})
export class ChatbotComponent {
  @ViewChild('scroll') scroll?: ElementRef<HTMLElement>;
  private readonly api=inject(AssistantService); readonly language=inject(LanguageService);
  open=false;loading=false;initializing=false;receivingTokens=false;showHistory=false;error='';draft='';health?:ChatbotHealth;conversation?:Conversation;conversations:Conversation[]=[];suggestions:string[]=[];lastRenderMs=0;private abortController?:AbortController;private streamSubscription?:Subscription;

  toggle(){this.open=!this.open;if(this.open&&!this.health&&!this.initializing)this.initialize();}
  initialize(){this.initializing=true;this.error='';forkJoin({health:this.api.health(),suggestions:this.api.suggestions(),conversations:this.api.list()}).pipe(finalize(()=>this.initializing=false)).subscribe({next:({health,suggestions,conversations})=>{this.health=health;this.suggestions=suggestions.suggestions;this.conversations=Array.isArray(conversations)?conversations:conversations.results??[];if(!health.ollama)this.error=this.language.translate('chat.ollamaUnavailable');else if(!health.model_available)this.error=this.language.translate('chat.modelUnavailable');},error:()=>this.error=this.language.translate('chat.backendUnavailable')});}
  ask(text=this.draft){const content=text.trim();if(!content||this.loading||this.health?.ollama===false||this.health?.model_available===false)return;const requestId=crypto.randomUUID(),now=new Date().toISOString();this.loading=true;this.receivingTokens=false;this.error='';this.draft='';this.abortController=new AbortController();const current=this.conversation??{id:0,language:this.language.current,messages:[],created_at:now,updated_at:now};this.conversation={...current,messages:[...current.messages,{id:-Date.now(),role:'USER',content,sources:[],request_id:requestId,created_at:now}]};this.streamSubscription=this.api.stream(content,this.language.current,requestId,current.id||undefined,this.abortController.signal).pipe(finalize(()=>{this.loading=false;this.receivingTokens=false;this.abortController=undefined;})).subscribe({next:item=>{if(item.event==='meta'&&this.conversation)this.conversation={...this.conversation,id:item.data.conversation_id};if(item.event==='token'){this.receivingTokens=true;this.appendToken(requestId,item.data.content);}if(item.event==='done'&&this.conversation){this.replaceFinalMessage(requestId,item.data.message);this.conversations=[this.conversation,...this.conversations.filter(value=>value.id!==this.conversation!.id)];}if(item.event==='error')this.error=item.data.detail;requestAnimationFrame(()=>this.scroll?.nativeElement.scrollTo({top:99999,behavior:'smooth'}));},error:response=>this.error=response?.detail??this.language.translate('common.error')});}
  stopGeneration(){this.abortController?.abort();this.streamSubscription?.unsubscribe();}
  private appendToken(requestId:string,token:string){if(!this.conversation)return;const messages=[...this.conversation.messages];const index=messages.findIndex(message=>message.role==='ASSISTANT'&&message.request_id===requestId);if(index>=0)messages[index]={...messages[index],content:messages[index].content+token};else messages.push({id:-(Date.now()+1),role:'ASSISTANT',content:token,sources:[],request_id:requestId,created_at:new Date().toISOString()});this.conversation={...this.conversation,messages};}
  private replaceFinalMessage(requestId:string,message:ChatMessage){if(!this.conversation)return;const messages=[...this.conversation.messages];const temporaryIndex=messages.findIndex(item=>item.role==='ASSISTANT'&&item.request_id===requestId);if(temporaryIndex>=0)messages.splice(temporaryIndex,1,message);else{const userIndex=messages.findIndex(item=>item.role==='USER'&&item.request_id===requestId);messages.splice(userIndex>=0?userIndex+1:messages.length,0,message);}this.conversation={...this.conversation,messages};}
  selectConversation(conversation:Conversation){this.conversation=this.withUniqueMessages(conversation);this.showHistory=false;this.error='';}
  newConversation(){if(this.loading)return;this.conversation=undefined;this.draft='';this.error='';this.showHistory=false;}
  retryHealth(){this.health=undefined;this.initialize();}
  track(_:number,message:ChatMessage){return message.id;} trackConversation(_:number,conversation:Conversation){return conversation.id;}
  sourceLabel(type:string,name:string){if(type==='aggregate')return name;return ({application:'Candidatures',internship:'Stagiaires',training:'Formations',bu:'Business Units'} as Record<string,string>)[type]??name;}
  private withUniqueMessages(conversation:Conversation):Conversation {
    const seen=new Set<number>();
    return {...conversation,messages:conversation.messages.filter(message=>!seen.has(message.id)&&!!seen.add(message.id))};
  }
}
