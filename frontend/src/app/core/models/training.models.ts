export type TrainingStatus = 'DRAFT' | 'PUBLISHED' | 'ARCHIVED';
export type SessionStatus = 'PLANNED' | 'OPEN' | 'FULL' | 'IN_PROGRESS' | 'COMPLETED' | 'CANCELLED';
export type EnrollmentStatus = 'PENDING_MANAGER' | 'REJECTED_BY_MANAGER' | 'PENDING_SUPER_ADMIN' | 'REJECTED_BY_SUPER_ADMIN' | 'APPROVED' | 'ENROLLED' | 'COMPLETED' | 'CANCELLED';

export interface TrainingSession {
  id: number;
  training: number;
  start_date: string;
  end_date: string;
  start_time: string;
  end_time: string;
  location: string;
  online_link: string;
  trainer: number | null;
  maximum_participants: number;
  participant_count: number;
  remaining_capacity: number;
  status: SessionStatus;
  external_client: number | null;
}

export interface Training {
  id: number;
  title: string;
  description: string;
  training_type: string;
  category: string;
  objectives: string;
  prerequisites: string;
  duration: number;
  delivery_mode: string;
  level: string;
  trainer: number | null;
  business_unit: number | null;
  external_client: number | null;
  project_name: string;
  associated_link: string;
  status: TrainingStatus;
  sessions: TrainingSession[];
}

export interface EnrollmentHistory {
  id: number;
  previous_status: string;
  new_status: string;
  changed_by_email: string;
  comment: string;
  timestamp: string;
}

export interface TrainingEnrollment {
  id: number;
  user: number;
  user_email: string;
  training: number;
  training_title: string;
  user_name: string;
  project_name: string;
  business_unit: number;
  session: number;
  session_start_date: string;
  session_end_date: string;
  present_days: number;
  requested_at: string;
  status: EnrollmentStatus;
  final_status: EnrollmentStatus;
  manager_comment: string;
  super_admin_comment: string;
  history: EnrollmentHistory[];
}

export interface ClientTraining {
  id: number;
  title: string;
  project_name: string;
  associated_link: string;
  sessions: Omit<TrainingSession, 'training' | 'trainer' | 'maximum_participants' | 'participant_count' | 'remaining_capacity' | 'external_client'>[];
}

export type AttendanceStatus = 'PRESENT' | 'ABSENT' | 'LATE' | 'EXCUSED';
export interface AttendanceHistory { id:number; status:AttendanceStatus; validated:boolean; changed_by_email:string; note:string; timestamp:string; }
export interface SessionAttendance { id:number; enrollment:number; session:number; user_email:string; user_name:string; training_title:string; date:string; status:AttendanceStatus; note:string; validated:boolean; validated_by:number|null; validated_by_email:string|null; validated_at:string|null; updated_at:string; history:AttendanceHistory[]; }
export interface TrainingCertificate { id:number; enrollment:number; user_email:string; training_title:string; session:number; certificate_number:string; issued_at:string; download_url:string; }
export const ATTENDANCE_STATUS_LABELS: Record<AttendanceStatus,string> = { PRESENT:'Présent', ABSENT:'Absent', LATE:'En retard', EXCUSED:'Absence justifiée' };

export const TRAINING_STATUS_LABELS: Record<string, string> = { DRAFT: 'Brouillon', PUBLISHED: 'Publiée', ARCHIVED: 'Archivée' };
export const SESSION_STATUS_LABELS: Record<string, string> = { PLANNED: 'Planifiée', OPEN: 'Inscriptions ouvertes', FULL: 'Complète', IN_PROGRESS: 'En cours', COMPLETED: 'Terminée', CANCELLED: 'Annulée' };
export const ENROLLMENT_STATUS_LABELS: Record<string, string> = { PENDING_MANAGER: 'En attente du manager', REJECTED_BY_MANAGER: 'Refusée par le manager', PENDING_SUPER_ADMIN: 'En attente du Super Admin', REJECTED_BY_SUPER_ADMIN: 'Refusée par le Super Admin', APPROVED: 'Approuvée', ENROLLED: 'Inscrit', COMPLETED: 'Terminée', CANCELLED: 'Annulée' };
