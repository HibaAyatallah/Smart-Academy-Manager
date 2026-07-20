export type UserRole =
  | 'SUPER_ADMIN'
  | 'HR'
  | 'BU_MANAGER'
  | 'TRAINER_TUTOR'
  | 'EMPLOYEE'
  | 'INTERN'
  | 'CANDIDATE'
  | 'CLIENT';

export interface LoginRequest {
  email: string;
  password: string;
}

export interface AuthTokens {
  access: string;
  refresh: string;
}

export interface RefreshTokenResponse {
  access: string;
  refresh?: string;
}

export interface UserProfile {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  full_name: string;
  phone_number: string;
  role: UserRole;
  is_active?: boolean;
  is_staff?: boolean;
  created_at?: string;
  updated_at?: string;
  business_units?: Array<{ id: number; name: string; code: string }>;
}

export const ROLE_LABELS: Record<UserRole, string> = {
  SUPER_ADMIN: 'Super administrateur',
  HR: 'Ressources humaines',
  BU_MANAGER: 'Manager BU',
  TRAINER_TUTOR: 'Formateur',
  EMPLOYEE: 'Collaborateur',
  INTERN: 'Stagiaire',
  CANDIDATE: 'Candidat',
  CLIENT: 'Client externe',
};
