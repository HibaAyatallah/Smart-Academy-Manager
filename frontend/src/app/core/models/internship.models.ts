export type InternshipStatus = 'UPCOMING' | 'ACTIVE' | 'SUSPENDED' | 'COMPLETED' | 'CANCELLED';
export type InternDocumentType = 'CONVENTION' | 'INSURANCE' | 'SCHOOL_CERT' | 'NDA' | 'OTHER';
export type EvaluationType = 'INITIAL' | 'MIDTERM' | 'FINAL';

export interface InternDocument {
  id: number; intern: number; document_type: InternDocumentType; file: string;
  is_validated: boolean; validated_at: string | null; validator: number | null;
  validator_email: string; comment: string; uploaded_at: string;
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
  subject_title: string; specification_pdf: string | null; internship_start: string | null;
  internship_end: string | null; current_status: InternshipStatus; progress: number;
  final_decision: string; documents: InternDocument[]; evaluations: InternEvaluation[]; created_at: string;
}

export interface HRBusinessUnitGroup {
  bu_id: number | null; bu_name: string; bu_code: string; manager_name: string;
  members: Array<{ id: number; email: string; full_name: string }>;
}

export const INTERNSHIP_STATUS_LABELS: Record<string, string> = { UPCOMING: 'À venir', ACTIVE: 'En cours', SUSPENDED: 'Suspendu', COMPLETED: 'Terminé', CANCELLED: 'Annulé' };
export const INTERN_DOCUMENT_LABELS: Record<string, string> = { CONVENTION: 'Convention de stage', INSURANCE: 'Assurance', SCHOOL_CERT: 'Attestation de scolarité', NDA: 'Accord de confidentialité', OTHER: 'Autre document' };
export const EVALUATION_TYPE_LABELS: Record<string, string> = { INITIAL: 'Évaluation initiale', MIDTERM: 'Évaluation à mi-parcours', FINAL: 'Évaluation finale' };
