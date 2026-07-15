import { routes } from './app.routes';

describe('Business Unit routes', () => {
  it('exposes only implemented BU pages and preserves role restrictions', () => {
    const privateShell = routes.find((route) => route.canActivate?.length && route.children);
    const businessUnits = privateShell?.children?.find((route) => route.path === 'business-units');
    expect(businessUnits?.data?.['roles']).toEqual(['SUPER_ADMIN', 'HR', 'BU_MANAGER']);
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
