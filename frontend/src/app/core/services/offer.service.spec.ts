import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { OfferCreateUpdate } from '../models/offer.models';
import { OfferService, serializeOfferDate } from './offer.service';

describe('OfferService date serialization', () => {
  let service: OfferService;
  let http: HttpTestingController;
  const basePayload: OfferCreateUpdate = {
    title: 'Backend Engineer', description: 'Description', business_unit: 1,
    application_type: 'HIRING',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(OfferService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('sends create dates as YYYY-MM-DD', () => {
    service.createOffer({
      ...basePayload,
      start_date: new Date(2026, 7, 28),
      end_date: new Date(2026, 10, 1),
      application_deadline: '9/30/2026',
    }).subscribe();

    const request = http.expectOne(req => req.url.endsWith('/offers/'));
    expect(request.request.method).toBe('POST');
    expect(request.request.body).toEqual(jasmine.objectContaining({
      start_date: '2026-08-28', end_date: '2026-11-01', application_deadline: '2026-09-30',
    }));
    request.flush({});
  });

  it('sends update dates as YYYY-MM-DD', () => {
    service.updateOffer(7, {
      start_date: new Date(2027, 0, 5), end_date: '2027-02-06', application_deadline: '3/7/2027',
    }).subscribe();

    const request = http.expectOne(req => req.url.endsWith('/offers/7/'));
    expect(request.request.method).toBe('PATCH');
    expect(request.request.body).toEqual({
      start_date: '2027-01-05', end_date: '2027-02-06', application_deadline: '2027-03-07',
    });
    request.flush({});
  });

  it('uses local calendar parts and does not shift a Date through UTC', () => {
    const localDate = new Date(2026, 7, 28, 0, 0, 0);
    expect(serializeOfferDate(localDate)).toBe('2026-08-28');
    expect(serializeOfferDate('2026-08-28T23:00:00.000Z')).toBe('2026-08-28');
  });
});
