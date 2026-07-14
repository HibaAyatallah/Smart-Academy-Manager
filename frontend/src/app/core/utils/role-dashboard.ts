import { UserRole } from '../models/auth.models';

export const ROLE_DASHBOARD_PATHS: Record<UserRole, string> = {
  SUPER_ADMIN: '/dashboard/super-admin',
  HR: '/dashboard/hr',
  BU_MANAGER: '/dashboard/business-unit',
  TRAINER_TUTOR: '/dashboard/training',
  EMPLOYEE: '/dashboard/employee',
  INTERN: '/dashboard/intern',
  CANDIDATE: '/dashboard/candidate',
  CLIENT: '/dashboard/client',
};

