import { routes } from './app.routes';

describe('Application routes', () => {
  it('exposes the public offer list and detail without an auth guard', () => {
    const publicShell = routes.find((route) => !route.canActivate?.length && route.children);
    const list = publicShell?.children?.find((route) => route.path === 'offres');
    const detail = publicShell?.children?.find((route) => route.path === 'offres/:id');
    expect(list).toBeDefined();
    expect(detail).toBeDefined();
    expect(list?.canActivate).toBeUndefined();
    expect(detail?.canActivate).toBeUndefined();
    expect(list?.loadComponent).toBeDefined();
    expect(detail?.loadComponent).toBeDefined();
  });

  it('exposes connected routes before the wildcard', () => {
    const privateShell = routes.find((route) => route.canActivate?.length && route.children);
    expect(privateShell?.canActivateChild?.length).toBeGreaterThan(0);
    const privatePaths = privateShell?.children?.map((route) => route.path) ?? [];
    expect(privatePaths).not.toContain('candidate/applications');
    expect(privatePaths).toContain('notifications');
    expect(privatePaths).toContain('reports');
    expect(privatePaths).toContain('audit-logs');
    expect(routes.at(-1)?.path).toBe('**');
  });

  it('applies the requested role restrictions to connected routes', () => {
    const privateShell = routes.find((route) => route.canActivate?.length && route.children);
    const notifications = privateShell?.children?.find((route) => route.path === 'notifications');
    const reports = privateShell?.children?.find((route) => route.path === 'reports');
    const auditLogs = privateShell?.children?.find((route) => route.path === 'audit-logs');

    expect(notifications?.data?.['roles']).toBeUndefined();
    expect(notifications?.canActivate).toBeUndefined();
    expect(reports?.data?.['roles']).toEqual(['SUPER_ADMIN']);
    expect(reports?.canActivate?.length).toBeGreaterThan(0);
    expect(auditLogs?.data?.['roles']).toEqual(['SUPER_ADMIN']);
    expect(auditLogs?.canActivate?.length).toBeGreaterThan(0);
  });
  it('restricts user management pages to the Super Admin', () => {
    const privateShell = routes.find((route) => route.canActivate?.length && route.children);
    for (const path of ['users', 'users/new', 'users/:id/edit']) {
      const route = privateShell?.children?.find((child) => child.path === path);
      expect(route?.data?.['roles']).toEqual(['SUPER_ADMIN']);
      expect(route?.canActivate?.length).toBeGreaterThan(0);
    }
  });

  it('exposes role-protected training workflow routes', () => {
    const privateShell = routes.find((route) => route.canActivate?.length && route.children);
    const catalogue = privateShell?.children?.find((child) => child.path === 'trainings');
    const approvals = privateShell?.children?.find((child) => child.path === 'training-enrollments');
    const participants = privateShell?.children?.find((child) => child.path === 'training-participants');
    const client = privateShell?.children?.find((child) => child.path === 'client-trainings');
    expect(catalogue?.data?.['roles']).toContain('TRAINER_TUTOR');
    expect(approvals?.data?.['roles']).toContain('BU_MANAGER');
    expect(client?.data?.['roles']).toEqual(['CLIENT']);
    const attendance = privateShell?.children?.find((child) => child.path === 'attendance-certificates');
    expect(attendance?.data?.['roles']).toEqual(['SUPER_ADMIN', 'BU_MANAGER', 'TRAINER_TUTOR']);
    expect(approvals?.data?.['roles']).toEqual(['SUPER_ADMIN', 'BU_MANAGER', 'TRAINER_TUTOR']);
    expect(participants?.data?.['roles']).toEqual(['SUPER_ADMIN']);
    expect(catalogue?.data?.['roles']).not.toContain('EMPLOYEE');
    expect(approvals?.data?.['roles']).not.toContain('EMPLOYEE');
  });

  it('separates intern self-service from internship administration', () => {
    const privateShell = routes.find((route) => route.canActivate?.length && route.children);
    const own = privateShell?.children?.find((child) => child.path === 'internships/me');
    const detail = privateShell?.children?.find((child) => child.path === 'internships/:id');
    const list = privateShell?.children?.find((child) => child.path === 'internships');
    expect(own?.data?.['roles']).toEqual(['INTERN']);
    expect(detail?.data?.['roles']).toContain('EMPLOYEE');
    expect(detail?.data?.['roles']).toContain('TRAINER_TUTOR');
    expect(list?.data?.['roles']).toContain('EMPLOYEE');
    expect(list?.data?.['roles']).toContain('TRAINER_TUTOR');
    expect(list?.data?.['roles']).not.toContain('HR');
  });

  it('protects project management and excludes HR', () => {
    const privateShell = routes.find((route) => route.canActivate?.length && route.children);
    const list = privateShell?.children?.find((child) => child.path === 'projects');
    const detail = privateShell?.children?.find((child) => child.path === 'projects/:id');
    const create = privateShell?.children?.find((child) => child.path === 'projects/new');
    expect(list?.data?.['roles']).toEqual(['SUPER_ADMIN', 'EMPLOYEE']);
    expect(detail?.data?.['roles']).toEqual(['SUPER_ADMIN', 'EMPLOYEE']);
    expect(create?.data?.['roles']).toEqual(['SUPER_ADMIN', 'EMPLOYEE']);
  });


  it('exposes only implemented BU pages and preserves role restrictions', () => {
    const privateShell = routes.find((route) => route.canActivate?.length && route.children);
    const businessUnits = privateShell?.children?.find((route) => route.path === 'business-units');
    expect(businessUnits?.data?.['roles']).toEqual(['SUPER_ADMIN', 'BU_MANAGER', 'HR']);
    const paths = businessUnits?.children?.map((route) => route.path) ?? [];
    expect(paths).toContain('');
    expect(paths).toContain('needs');
    expect(paths).toContain('needs/new');
    expect(paths).toContain(':id');
    expect(paths).toContain(':id/needs/:needId');
    expect(paths).toContain(':id/needs/:needId/edit');
    expect(paths).toContain('members');
    expect(paths).not.toContain('new');
  });

  it('restricts need creation and editing routes to BU managers', () => {
    const privateShell = routes.find((route) => route.canActivate?.length && route.children);
    const businessUnits = privateShell?.children?.find((route) => route.path === 'business-units');
    const protectedPaths = ['needs/new', ':id/needs/:needId/edit'];
    for (const path of protectedPaths) {
      const route = businessUnits?.children?.find((child) => child.path === path);
      expect(route?.data?.['roles']).toEqual(['BU_MANAGER']);
      expect(route?.canActivate?.length).toBeGreaterThan(0);
    }
  });
});
