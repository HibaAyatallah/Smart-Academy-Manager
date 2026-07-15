import { UserRole } from '../models/auth.models';

export interface NavigationItem {
  label: string;
  icon: string;
  route: string;
  roles: readonly UserRole[];
  exact?: boolean;
}

export interface NavigationSection {
  label: string;
  items: readonly NavigationItem[];
}

const ALL_ROLES: readonly UserRole[] = [
  'SUPER_ADMIN', 'HR', 'BU_MANAGER', 'TRAINER_TUTOR',
  'EMPLOYEE', 'INTERN', 'CANDIDATE', 'CLIENT',
];

const ADMIN_ROLES: readonly UserRole[] = ['SUPER_ADMIN', 'HR'];
const BU_ROLES: readonly UserRole[] = ['SUPER_ADMIN', 'HR', 'BU_MANAGER'];

export const AUTHENTICATED_NAVIGATION: readonly NavigationSection[] = [
  {
    label: 'Vue d’ensemble',
    items: [
      { label: 'Tableau de bord', icon: 'space_dashboard', route: '/dashboard', roles: ALL_ROLES },
    ],
  },
  {
    label: 'Recrutement',
    items: [
      { label: 'Candidatures', icon: 'assignment_ind', route: '/applications', roles: ADMIN_ROLES, exact: true },
      { label: 'Mes candidatures', icon: 'description', route: '/applications/my', roles: ['CANDIDATE'] },
    ],
  },
  {
    label: 'Organisation',
    items: [
      { label: 'Business Units', icon: 'domain', route: '/business-units', roles: BU_ROLES, exact: true },
      { label: 'Besoins des BU', icon: 'fact_check', route: '/business-units/needs', roles: BU_ROLES },
    ],
  },
];

export function navigationForRole(role: UserRole): NavigationSection[] {
  return AUTHENTICATED_NAVIGATION
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => item.roles.includes(role)),
    }))
    .filter((section) => section.items.length > 0);
}
