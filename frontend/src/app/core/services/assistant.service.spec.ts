import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { AssistantService, Conversation } from './assistant.service';

describe('AssistantService', () => {
  let service: AssistantService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AssistantService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('asks “Combien d’utilisateurs ?” as JSON and preserves the request id', () => {
    const requestId = 'd96a0877-7f4d-4f64-b82c-c6ad5c50a901';
    const events: Array<{event: string; data: any}> = [];
    service.stream('Combien d’utilisateurs ?', 'fr', requestId).subscribe(value => events.push(value));

    const request = http.expectOne('/api/chatbot/messages/');
    expect(request.request.method).toBe('POST');
    expect(request.request.headers.get('Accept')).toBe('application/json');
    expect(request.request.headers.get('Content-Type')).toBe('application/json');
    expect(request.request.body).toEqual({
      message: 'Combien d’utilisateurs ?', language: 'fr', request_id: requestId, conversation_id: undefined,
    });

    const response: Conversation = {
      id: 12, language: 'fr', created_at: '2026-08-04T10:00:00Z', updated_at: '2026-08-04T10:00:01Z',
      messages: [
        {id: 1, role: 'USER', content: 'Combien d’utilisateurs ?', request_id: requestId, created_at: '2026-08-04T10:00:00Z'},
        {id: 2, role: 'ASSISTANT', content: 'Il y a 2 utilisateurs.', request_id: requestId, created_at: '2026-08-04T10:00:01Z'},
      ],
    };
    request.flush(response);

    expect(events.map(value => value.event)).toEqual(['meta', 'done']);
    expect(events[1].data.request_id).toBe(requestId);
    expect(events[1].data.message.request_id).toBe(requestId);
  });
});
