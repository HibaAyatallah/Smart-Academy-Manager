import { navigationForRole } from './authenticated-navigation';

const labelsFor = (role: Parameters<typeof navigationForRole>[0]) =>
  navigationForRole(role).flatMap((section) => section.items.map((item) => item.label));

describe('authenticated navigation', () => {
  it('gives HR and Super Admin equivalent navigation', () => {
    expect(labelsFor('HR')).toEqual(labelsFor('SUPER_ADMIN'));
  });

  it('limits candidate navigation to implemented candidate pages', () => {
    expect(labelsFor('CANDIDATE')).toEqual(['Tableau de bord', 'Mes candidatures']);
    expect(labelsFor('CANDIDATE')).not.toContain('Business Units');
  });

  it('gives BU Managers only the implemented BU destinations', () => {
    expect(labelsFor('BU_MANAGER')).toEqual([
      'Tableau de bord', 'Business Units', 'Besoins des BU',
    ]);
  });

  it('hides empty sections for roles with dashboard-only access', () => {
    const sections = navigationForRole('INTERN');
    expect(sections.length).toBe(1);
    expect(sections[0].items[0].label).toBe('Tableau de bord');
  });
});
