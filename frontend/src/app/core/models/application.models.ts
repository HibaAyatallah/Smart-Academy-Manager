import { UserRole } from './auth.models';

export type ApplicationType = 'PFA_INTERNSHIP' | 'PFE_INTERNSHIP' | 'HIRING';

export type ApplicationStatus =
  | 'RECEIVED'
  | 'UNDER_REVIEW'
  | 'PRESELECTED'
  | 'INTERVIEW'
  | 'ACCEPTED'
  | 'REJECTED'
  | 'ARCHIVED';

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
  offer?: number | null;
  offer_title?: string;
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
  cv_analysis?: CVAnalysis | null;
  conversion?: ApplicationConversionState | null;
}

export type ApplicationConversionType = 'INTERN' | 'EMPLOYEE';

export interface ApplicationConversionState {
  type: ApplicationConversionType;
  profile_id: number;
}

export interface ApplicationConversionPayload {
  conversion_type: ApplicationConversionType;
  business_unit: number;
  supervisor?: number | null;
  school?: string;
  specialization?: string;
  internship_type?: string;
  paid?: boolean;
  internship_start?: string | null;
  internship_end?: string | null;
  subject_title?: string;
  specification_pdf?: File | null;
}

export interface ApplicationConversionResponse {
  detail: string;
  conversion_type: ApplicationConversionType;
  profile_id: number;
  login_email: string;
  credentials_preserved: boolean;
  application: Application;
}

export interface CVExperience { position: string; company: string; start_date: string; end_date: string; duration: string; description: string; }
export interface CVEducation { title: string; institution: string; start_date: string; end_date: string; }
export interface CVAnalysis {
  id: number; first_name: string; last_name: string; full_name: string; email: string; phone: string; location: string;
  skills: string[]; experiences: CVExperience[]; education: CVEducation[]; diplomas: string[]; companies: string[];
  positions: string[]; languages: string[]; certifications: string[]; extraction_method: string;
  extraction_warnings: string[]; extractor_version: string; human_validated: boolean; validated_at: string | null;
}

export interface MatchScoreComponent {
  score: number | null; weight: number; available: boolean;
  candidate_years?: number | null; required_years?: number | null; explanation?: string;
}

export interface ApplicationMatch {
  id: number; application: number; offer: number; offer_title: string; candidate_name: string;
  score: number; matched_skills: string[]; missing_skills: string[]; additional_skills: string[];
  score_breakdown: Record<string, MatchScoreComponent | number | string>;
  candidate_summary: string; explanation: string; algorithm_version: string;
  semantic_score: number | null; semantic_model: string;
  human_decision: 'PENDING' | 'APPROVED' | 'REJECTED'; reviewed_at: string | null;
  created_at: string; updated_at: string;
}

export interface CandidateRankingRow {
  rank: number | null; application: number; candidate_name: string; submitted_at: string;
  relationship: 'APPLIED_TO_OFFER' | 'OTHER_APPLICATION' | 'TALENT_POOL';
  relationship_label: string; applied_to_current_offer: boolean;
  source_offer: number | null; source_offer_title: string;
  analysis_error: string; match: ApplicationMatch | null;
  score_details: Record<string, MatchScoreComponent | number | string> | null;
  match_label: string;
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
  HIRING: 'Candidature spontanée',
};

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  RECEIVED: 'T0 - Candidature déposée',
  UNDER_REVIEW: 'En cours d’étude',
  PRESELECTED: 'T1 - Présélectionné',
  INTERVIEW: 'T1 - Entretien',
  ACCEPTED: 'T2 - Accepté',
  REJECTED: 'Refusé',
  ARCHIVED: 'Archivé',
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
