import { Routes } from '@angular/router';

import { authGuard } from './core/guards/auth.guard';
import { roleGuard } from './core/guards/role.guard';
import { UserRole } from './core/models/auth.models';

const dashboardRoute = (path: string, role: UserRole, title: string): Routes[number] => ({
  path,
  canActivate: [roleGuard],
  data: {
    roles: [role],
    title,
  },
  loadComponent: () =>
    import('./features/dashboard/dashboard.component').then(
      (component) => component.DashboardComponent,
    ),
});

export const routes: Routes = [
  // Redirections de compatibilité
  { path: 'apply', redirectTo: 'candidature', pathMatch: 'full' },
  { path: 'login', redirectTo: 'connexion', pathMatch: 'full' },

  // Espace Public
  {
    path: '',
    loadComponent: () => import('./layouts/public-layout/public-layout.component').then(m => m.PublicLayoutComponent),
    children: [
      { path: '', loadComponent: () => import('./pages/public/home/home.component').then(m => m.HomeComponent), pathMatch: 'full' },
      { path: 'groupe', loadComponent: () => import('./pages/public/about/about.component').then(m => m.AboutComponent) },
      { path: 'expertises', loadComponent: () => import('./pages/public/careers/careers.component').then(m => m.CareersComponent) },
      { path: 'recrutement', loadComponent: () => import('./pages/public/recruitment/recruitment.component').then(m => m.RecruitmentComponent) },
      { path: 'contact', loadComponent: () => import('./pages/public/contact/contact.component').then(m => m.ContactComponent) },
      { path: 'politique-confidentialite', loadComponent: () => import('./pages/public/privacy/privacy.component').then(m => m.PrivacyComponent) },
      { path: 'mentions-legales', loadComponent: () => import('./pages/public/legal/legal.component').then(m => m.LegalComponent) },
      { path: 'candidature', loadComponent: () => import('./features/applications/public-application-form/public-application-form.component').then(m => m.PublicApplicationFormComponent) },
    ]
  },

  // Espace Auth
  {
    path: '',
    loadComponent: () => import('./layouts/auth-layout/auth-layout.component').then(m => m.AuthLayoutComponent),
    children: [
      { path: 'connexion', loadComponent: () => import('./features/auth/login/login.component').then(m => m.LoginComponent) },
    ]
  },

  // Espace Privé (inchangé)
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./layouts/main-layout/main-layout.component').then(m => m.MainLayoutComponent),
    children: [
      { path: 'espace-personnel', data: { title: 'Mon espace personnel' }, loadComponent: () => import('./features/personal-space/personal-space.component').then(m => m.PersonalSpaceComponent) },
      {
        path: 'dashboard',
        pathMatch: 'full',
        loadComponent: () => import('./features/dashboard/dashboard-redirect.component').then(m => m.DashboardRedirectComponent),
      },
      {
        path: 'applications/my',
        canActivate: [roleGuard],
        data: { roles: ['CANDIDATE'], title: 'Mes candidatures' },
        loadComponent: () => import('./features/applications/candidate-applications/candidate-applications.component').then(m => m.CandidateApplicationsComponent),
      },
      {
        path: 'applications/:id',
        canActivate: [roleGuard],
        data: { roles: ['SUPER_ADMIN', 'HR'], title: 'Détail de la candidature' },
        loadComponent: () => import('./features/applications/application-detail/application-detail.component').then(m => m.ApplicationDetailComponent),
      },
      {
        path: 'applications',
        canActivate: [roleGuard],
        data: { roles: ['SUPER_ADMIN', 'HR'], title: 'Candidatures' },
        loadComponent: () => import('./features/applications/hr-application-list/hr-application-list.component').then(m => m.HrApplicationListComponent),
      },
      dashboardRoute('dashboard/super-admin', 'SUPER_ADMIN', 'Dashboard super administrateur'),
      dashboardRoute('dashboard/hr', 'HR', 'Dashboard RH'),
      dashboardRoute('dashboard/business-unit', 'BU_MANAGER', 'Dashboard Business Unit'),
      dashboardRoute('dashboard/training', 'TRAINER_TUTOR', 'Dashboard formateur / tuteur'),
      dashboardRoute('dashboard/employee', 'EMPLOYEE', 'Dashboard collaborateur'),
      dashboardRoute('dashboard/intern', 'INTERN', 'Dashboard stagiaire'),
      dashboardRoute('dashboard/candidate', 'CANDIDATE', 'Dashboard candidat'),
      dashboardRoute('dashboard/client', 'CLIENT', 'Dashboard client'),
      // Business Units Routes
      {
        path: 'business-units',
        canActivate: [roleGuard],
        data: { roles: ['SUPER_ADMIN', 'HR', 'BU_MANAGER'], title: 'Business Units' },
        children: [
          {
            path: '',
            loadComponent: () => import('./features/business-units/bu-list/bu-list').then(m => m.BuList),
          },
          {
            path: 'needs',
            data: { title: 'Besoins des Business Units' },
            loadComponent: () => import('./features/business-units/bu-needs-list/bu-needs-list').then(m => m.BuNeedsList),
          },
          {
            path: ':id',
            data: { title: 'Détail de la Business Unit' },
            loadComponent: () => import('./features/business-units/bu-detail/bu-detail').then(m => m.BuDetail),
          },
          {
            path: ':id/needs/:needId',
            data: { title: 'Détail du besoin' },
            loadComponent: () => import('./features/business-units/bu-need-detail/bu-need-detail').then(m => m.BuNeedDetail),
          },
        ]
      }
    ],
  },
  {
    path: '**',
    redirectTo: '',
  },
];
