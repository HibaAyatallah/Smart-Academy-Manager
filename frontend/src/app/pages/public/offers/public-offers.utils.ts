import { Offer } from '../../../core/models/offer.models';

export function isOfferOpen(offer: Offer, today = new Date()): boolean {
  if (offer.status !== 'PUBLISHED') return false;
  if (!offer.application_deadline) return true;
  const localToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const deadline = new Date(`${offer.application_deadline.slice(0, 10)}T00:00:00`);
  return !Number.isNaN(deadline.getTime()) && deadline >= localToday;
}

export function mainSkills(offer: Offer): string[] {
  return (offer.required_skills || '').split(/[,;\n]/).map(skill => skill.trim()).filter(Boolean).slice(0, 6);
}
