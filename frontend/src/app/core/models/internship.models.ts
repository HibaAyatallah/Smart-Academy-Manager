export type InternshipStatus = 'UPCOMING' | 'ACTIVE' | 'SUSPENDED' | 'COMPLETED' | 'CANCELLED';
export type InternDocumentType = 'CONVENTION' | 'INSURANCE' | 'SCHOOL_CERT' | 'NDA' | 'OTHER';
export type EvaluationType = 'INITIAL' | 'MIDTERM' | 'FINAL';

export interface InternDocument {
  id: number; intern: number; document_type: InternDocumentType; file: string;
  requirement: number | null; original_name: string; content_type: string; size: number;
  status: 'PENDING' | 'VALIDATED' | 'REJECTED';
  is_validated: boolean; validated_at: string | null; validator: number | null;
  validator_email: string; comment: string; uploaded_at: string;
}

export interface InternDocumentRequirement {
  id: number; document_type: InternDocumentType; name: string; description: string;
  is_required: boolean; due_date: string | null; is_active: boolean;
  latest_submission: InternDocument | null;
}

export interface InternEvaluation {
  id: number; intern: number; evaluation_type: EvaluationType;
  technical_skills: number; autonomy: number; communication: number; teamwork: number;
  deadline_respect: number; work_quality: number; professionalism: number;
  overall_score: number; comments: string; evaluator: number | null;
  evaluator_email: string; created_at: string;
}

export interface InternProfile {
  id: number; user: number; user_email: string; user_full_name: string;
  source_application: number | null; school: string; specialization: string;
  internship_type: string; paid: boolean; business_unit: number | null;
  business_unit_name: string; supervisor: number | null; supervisor_email: string;
  manager_name: string;
  subject_title: string; specification_pdf: string | null; internship_start: string | null;
  internship_end: string | null; current_status: InternshipStatus; progress: number;
  final_decision: string; documents: InternDocument[]; document_requirements: InternDocumentRequirement[]; evaluations: InternEvaluation[]; created_at: string;
}

export interface HRBusinessUnitGroup {
  bu_id: number | null; bu_name: string; bu_code: string; manager_name: string;
  members: Array<{ id: number; email: string; first_name: string; last_name: string; full_name: string; phone_number: string; is_active: boolean; created_at: string; position: string; joined_at: string | null }>;
}

export interface HRInternProfile {
  id: number; email: string; first_name: string; last_name: string; full_name: string; phone_number: string;
  school: string; specialization: string; internship_type: string; paid: boolean;
  internship_start: string | null; internship_end: string | null; subject_title: string;
  business_unit: { id: number; name: string; code: string } | null;
  supervisor: { id: number; full_name: string; email: string } | null;
  document_submission_status: { submitted_count: number; validated_count: number; has_documents: boolean; all_validated: boolean };
}

export const INTERNSHIP_STATUS_LABELS: Record<string, string> = { UPCOMING: 'À venir', ACTIVE: 'En cours', SUSPENDED: 'Suspendu', COMPLETED: 'Terminé', CANCELLED: 'Annulé' };
export const INTERN_DOCUMENT_LABELS: Record<string, string> = { CONVENTION: 'Convention de stage', INSURANCE: 'Assurance', SCHOOL_CERT: 'Attestation de scolarité', NDA: 'Accord de confidentialité', OTHER: 'Autre document' };
export const EVALUATION_TYPE_LABELS: Record<string, string> = { INITIAL: 'Évaluation initiale', MIDTERM: 'Évaluation à mi-parcours', FINAL: 'Évaluation finale' };
