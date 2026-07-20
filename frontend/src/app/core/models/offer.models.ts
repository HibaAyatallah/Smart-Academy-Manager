import { ApplicationType, EducationLevel, PaginatedResponse } from './application.models';

export type OfferStatus = 'DRAFT' | 'PUBLISHED' | 'CLOSED' | 'ARCHIVED';

export interface Offer {
  id: number;
  title: string;
  description: string;
  business_unit: number;
  business_unit_name: string;
  application_type: ApplicationType;
  application_type_label: string;
  required_skills: string;
  required_level: EducationLevel | '';
  number_of_positions: number;
  location: string;
  start_date: string | null;
  end_date: string | null;
  application_deadline: string | null;
  publication_date: string | null;
  status: OfferStatus;
  status_label: string;
  created_by_email: string;
  created_at: string;
  updated_at: string;
}

export interface OfferCreateUpdate {
  title: string;
  description: string;
  business_unit: number;
  application_type: ApplicationType;
  required_skills?: string;
  required_level?: EducationLevel | '';
  number_of_positions?: number;
  location?: string;
  start_date?: string | null;
  end_date?: string | null;
  application_deadline?: string | null;
  publication_date?: string | null;
  status?: OfferStatus;
}

export const OFFER_STATUS_LABELS: Record<OfferStatus, string> = {
  DRAFT: 'Brouillon',
  PUBLISHED: 'Publiée',
  CLOSED: 'Fermée',
  ARCHIVED: 'Archivée',
};
