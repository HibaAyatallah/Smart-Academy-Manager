import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NoopAnimationsModule } from '@angular/platform-browser/animations';
import { provideRouter } from '@angular/router';
import { of, Subject } from 'rxjs';

import { AssistantService, Conversation } from '../../../core/services/assistant.service';
import { ChatbotComponent } from './chatbot.component';

describe('ChatbotComponent', () => {
  let fixture: ComponentFixture<ChatbotComponent>;
  let component: ChatbotComponent;
  let api: jasmine.SpyObj<AssistantService>;
  let pending: Subject<{event:string;data:any}>;

  const conversation = (messages: Conversation['messages'] = []): Conversation => ({
    id: 1,
    language: 'fr',
    messages,
    created_at: '2026-08-02T10:00:00Z',
    updated_at: '2026-08-02T10:00:00Z'
  });

  beforeEach(async () => {
    pending = new Subject<{event:string;data:any}>();
    api = jasmine.createSpyObj<AssistantService>('AssistantService', ['stream', 'health', 'suggestions', 'list']);
    api.stream.and.returnValue(pending);
    api.health.and.returnValue(of({backend:true,ollama:true,model:'test',model_available:true,error_code:null,streaming_supported:false}));
    api.suggestions.and.returnValue(of({suggestions:[]}));
    api.list.and.returnValue(of([]));
    await TestBed.configureTestingModule({
      imports: [ChatbotComponent, NoopAnimationsModule],
      providers: [{provide: AssistantService, useValue: api}, provideRouter([])]
    }).compileComponents();
    fixture = TestBed.createComponent(ChatbotComponent);
    component = fixture.componentInstance;
    component.open = true;
    component.health = {backend:true,ollama:true,model:'test',model_available:true,error_code:null,streaming_supported:false};
    fixture.detectChanges();
  });

  it('sends exactly one request when the submit button is clicked', () => {
    component.draft = 'bonjour';
    fixture.detectChanges();
    (fixture.nativeElement.querySelector('button[type="submit"]') as HTMLButtonElement).click();
    expect(api.stream).toHaveBeenCalledTimes(1);
  });

  it('sends exactly one request when the form is submitted by Enter', () => {
    component.draft = 'hello';
    fixture.detectChanges();
    fixture.nativeElement.querySelector('form').dispatchEvent(new Event('submit'));
    expect(api.stream).toHaveBeenCalledTimes(1);
  });

  it('disables sending while a request is in progress', () => {
    component.draft = 'salam';
    component.ask();
    fixture.detectChanges();
    expect((fixture.nativeElement.querySelector('button[type="submit"]') as HTMLButtonElement).disabled).toBeTrue();
    component.ask();
    expect(api.stream).toHaveBeenCalledTimes(1);
  });

  it('does not duplicate messages when a conversation is reopened', () => {
    const message = {id: 7, role: 'USER' as const, content: 'bonjour', created_at: '2026-08-02T10:00:00Z'};
    component.selectConversation(conversation([message, {...message}]));
    expect(component.conversation?.messages.length).toBe(1);
  });

  it('displays the greeting response once', () => {
    component.draft = 'bonjour';
    component.ask();
    const requestId=api.stream.calls.mostRecent().args[2];
    pending.next({event:'token',data:{request_id:requestId,content:'Bonjour ! Je suis l’assistant Smart Academy.'}});
    pending.next({event:'done',data:{request_id:requestId,message:{id:2,role:'ASSISTANT',content:'Bonjour ! Je suis l’assistant Smart Academy.',sources:[],request_id:requestId,created_at:'2026-08-02T10:00:01Z'}}});
    pending.complete();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Bonjour ! Je suis l’assistant Smart Academy.');
    expect(component.conversation?.messages.filter(item => item.content === 'bonjour').length).toBe(1);
  });

  it('stops the active generation and never starts two streams', () => {
    component.draft='formations';component.ask();component.ask('sessions');
    expect(api.stream).toHaveBeenCalledTimes(1);
    component.stopGeneration();
    expect(component['abortController']?.signal.aborted ?? true).toBeTrue();
  });

  it('keeps technical source metadata out of the user-count message', () => {
    component.draft='Combien d’utilisateurs ?';component.ask();const requestId=api.stream.calls.mostRecent().args[2];
    pending.next({event:'done',data:{message:{id:3,role:'ASSISTANT',content:'Il y a 50 utilisateurs.',request_id:requestId,created_at:new Date().toISOString(),sources:[{type:'aggregate',name:'Utilisateurs',reference:'USERS_TOTAL',id:null,url:'/users'}]}}});
    fixture.detectChanges();
    const assistantMessage=fixture.nativeElement.querySelector('.message:not(.user)');
    expect(assistantMessage.querySelector(':scope > span').textContent.trim()).toBe('Il y a 50 utilisateurs.');
    expect(assistantMessage.querySelector('details.sources')).not.toBeNull();
    expect(assistantMessage.textContent).toContain('Utilisateurs');
    expect(assistantMessage.textContent).not.toContain('USERS_TOTAL');
    expect(assistantMessage.textContent).not.toContain('aggregate');
  });

  it('keeps a final answer immediately after its matching user message', () => {
    component.selectConversation(conversation([
      {id:1,role:'USER',content:'ancienne',request_id:'old',created_at:new Date().toISOString()},
      {id:2,role:'ASSISTANT',content:'ancienne réponse',request_id:'old',created_at:new Date().toISOString()},
    ]));
    component.ask('nouvelle');
    const requestId=api.stream.calls.mostRecent().args[2];
    pending.next({event:'done',data:{request_id:requestId,message:{id:4,role:'ASSISTANT',content:'nouvelle réponse',sources:[],request_id:requestId,created_at:new Date().toISOString()}}});
    const messages=component.conversation!.messages;
    const userIndex=messages.findIndex(item=>item.role==='USER'&&item.request_id===requestId);
    expect(messages[userIndex+1].content).toBe('nouvelle réponse');
    expect(messages[userIndex+1].request_id).toBe(requestId);
  });
});
