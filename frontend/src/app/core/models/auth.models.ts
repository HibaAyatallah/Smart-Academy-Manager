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
