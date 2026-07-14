import { routes } from './app.routes';

describe('Business Unit routes', () => {
  it('exposes only implemented BU pages and preserves role restrictions', () => {
    const privateShell = routes.find((route) => route.canActivate?.length && route.children);
    const businessUnits = privateShell?.children?.find((route) => route.path === 'business-units');
    expect(businessUnits?.data?.['roles']).toEqual(['SUPER_ADMIN', 'HR', 'BU_MANAGER']);
    const paths = businessUnits?.children?.map((route) => route.path) ?? [];
    expect(paths).toContain('');
    expect(paths).toContain('needs');
    expect(paths).toContain(':id');
    expect(paths).toContain(':id/needs/:needId');
    expect(paths).not.toContain(':id/members');
    expect(paths).not.toContain('new');
  });
});
