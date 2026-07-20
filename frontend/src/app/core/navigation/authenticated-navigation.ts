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
const ADMIN_BU_ROLES: readonly UserRole[] = ['SUPER_ADMIN', 'HR'];

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
      { label: 'Offres', icon: 'work', route: '/offers', roles: ['SUPER_ADMIN', 'HR', 'CANDIDATE'] },
      { label: 'Candidatures', icon: 'assignment_ind', route: '/applications', roles: ADMIN_ROLES, exact: true },
      { label: 'Mes candidatures', icon: 'description', route: '/applications/my', roles: ['CANDIDATE'] },
    ],
  },
  {
    label: 'Organisation',
    items: [
      { label: 'Gestion des utilisateurs', icon: 'manage_accounts', route: '/users', roles: ['SUPER_ADMIN'] },
      { label: 'Business Units', icon: 'domain', route: '/business-units', roles: ADMIN_BU_ROLES, exact: true },
      { label: 'Besoins des BU', icon: 'fact_check', route: '/business-units/needs', roles: ADMIN_BU_ROLES },
      { label: 'Besoins de ma BU', icon: 'fact_check', route: '/business-units/needs', roles: ['BU_MANAGER'] },
      { label: 'Membres de ma BU', icon: 'groups', route: '/business-units/members', roles: ['BU_MANAGER'] },
      { label: 'Formations de ma BU', icon: 'school', route: '/my-business-unit/trainings', roles: ['EMPLOYEE'] },
    ],
  },
  {
    label: 'Formation',
    items: [
      { label: 'Catalogue et sessions', icon: 'school', route: '/trainings', roles: ['SUPER_ADMIN', 'HR', 'BU_MANAGER', 'TRAINER_TUTOR', 'EMPLOYEE', 'INTERN'] },
      { label: 'Inscriptions et validations', icon: 'how_to_reg', route: '/training-enrollments', roles: ['SUPER_ADMIN', 'HR', 'BU_MANAGER', 'TRAINER_TUTOR', 'EMPLOYEE', 'INTERN'] },
      { label: 'Présences et certificats', icon: 'workspace_premium', route: '/attendance-certificates', roles: ['SUPER_ADMIN', 'HR', 'TRAINER_TUTOR', 'EMPLOYEE', 'INTERN'] },
      { label: 'Mes formations client', icon: 'business_center', route: '/client-trainings', roles: ['CLIENT'] },
    ],
  },
  {
    label: 'Stages',
    items: [
      { label: 'Gestion des stagiaires', icon: 'badge', route: '/internships', roles: ['SUPER_ADMIN', 'HR', 'BU_MANAGER', 'EMPLOYEE'] },
      { label: 'Mon stage', icon: 'assignment', route: '/internships/me', roles: ['INTERN'] },
    ],
  },
  {
    label: 'Projets',
    items: [
      { label: 'Projets', icon: 'folder_open', route: '/projects', roles: ['SUPER_ADMIN', 'HR', 'EMPLOYEE', 'INTERN'] },
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
