import { UserRole } from './auth.models';

export type ApplicationType = 'PFA_INTERNSHIP' | 'PFE_INTERNSHIP' | 'HIRING';

export type ApplicationStatus =
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'PRESELECTED'
  | 'INTERVIEW_SCHEDULED'
  | 'INTERVIEW_COMPLETED'
  | 'ACCEPTED'
  | 'REJECTED'
  | 'CANCELLED';

export type ApplicationDocumentType = 'CV' | 'COVER_LETTER' | 'PERSONAL_PHOTO' | 'OTHER';

export type EducationLevel =
  | 'FIRST_YEAR'
  | 'SECOND_YEAR'
  | 'THIRD_YEAR'
  | 'FOURTH_YEAR'
  | 'FIFTH_YEAR'
  | 'BACHELOR'
  | 'MASTER'
  | 'ENGINEERING'
  | 'DOCTORATE'
  | 'OTHER';

export interface CandidateProfile {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  phone_number: string;
  current_school: string;
  study_level: EducationLevel;
  study_level_label: string;
  study_level_other: string;
  study_field: string;
  linkedin_url: string;
  portfolio_url: string;
  address: string;
}

export interface ApplicationDocument {
  id: number;
  application: number;
  document_type: ApplicationDocumentType;
  download_url: string;
  original_name: string;
  content_type: string;
  size: number;
  uploaded_by_email: string;
  uploaded_at: string;
}

export interface ApplicationInterview {
  id: number;
  application: number;
  scheduled_at: string;
  location: string;
  meeting_link: string;
  interviewer: number | null;
  interviewer_email: string;
  notes: string;
  result: string;
  created_by_email: string;
  created_at: string;
  updated_at: string;
}

export interface ApplicationStatusHistory {
  id: number;
  from_status: ApplicationStatus | '';
  to_status: ApplicationStatus;
  changed_by_email: string;
  comment: string;
  created_at: string;
}

export interface Application {
  id: number;
  candidate_profile: CandidateProfile;
  application_type: ApplicationType;
  application_type_label: string;
  status: ApplicationStatus;
  status_label: string;
  motivation_message: string;
  rejection_reason: string;
  submitted_at: string;
  updated_at: string;
  accepted_at: string | null;
  rejected_at: string | null;
  cancelled_at: string | null;
  retention_until: string | null;
  documents: ApplicationDocument[];
  interviews: ApplicationInterview[];
  status_history: ApplicationStatusHistory[];
}

export interface PaginatedResponse<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface ApplicationFilters {
  application_type?: ApplicationType | '';
  status?: ApplicationStatus | '';
  search?: string;
  page?: number;
}

export const APPLICATION_TYPE_LABELS: Record<ApplicationType, string> = {
  PFA_INTERNSHIP: 'Stage PFA',
  PFE_INTERNSHIP: 'Stage PFE',
  HIRING: 'Candidature pour embauche',
};

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  SUBMITTED: 'T0 - Candidature déposée',
  UNDER_REVIEW: 'En cours d’étude',
  PRESELECTED: 'T1 - Présélectionné',
  INTERVIEW_SCHEDULED: 'T1 - Entretien planifié',
  INTERVIEW_COMPLETED: 'Entretien réalisé',
  ACCEPTED: 'T2 - Accepté',
  REJECTED: 'Refusé',
  CANCELLED: 'Annulé',
};

export const EDUCATION_LEVEL_LABELS: Record<EducationLevel, string> = {
  FIRST_YEAR: '1re année',
  SECOND_YEAR: '2e année',
  THIRD_YEAR: '3e année',
  FOURTH_YEAR: '4e année',
  FIFTH_YEAR: '5e année',
  BACHELOR: 'Licence',
  MASTER: 'Master',
  ENGINEERING: 'Cycle ingénieur',
  DOCTORATE: 'Doctorat',
  OTHER: 'Autre',
};
