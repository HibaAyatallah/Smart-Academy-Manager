import { navigationForRole } from './authenticated-navigation';

const labelsFor = (role: Parameters<typeof navigationForRole>[0]) =>
  navigationForRole(role).flatMap((section) => section.items.map((item) => item.label));

describe('authenticated navigation', () => {
  it('reserves user management navigation for the Super Admin', () => {
    expect(labelsFor('SUPER_ADMIN')).toContain('Gestion des utilisateurs');
    expect(labelsFor('HR')).not.toContain('Gestion des utilisateurs');
  });

  it('limits candidate navigation to implemented candidate pages', () => {
    expect(labelsFor('CANDIDATE')).toEqual(['Tableau de bord', 'Offres', 'Mes candidatures']);
    expect(labelsFor('CANDIDATE')).not.toContain('Business Units');
  });

  it('gives BU Managers BU and training approval destinations', () => {
    expect(labelsFor('BU_MANAGER')).toEqual([
      'Tableau de bord', 'Besoins de ma BU', 'Membres de ma BU',
      'Catalogue et sessions', 'Inscriptions et validations',
      'Gestion des stagiaires',
    ]);
    expect(labelsFor('BU_MANAGER')).not.toContain('Business Units');
  });

  it('gives interns access to the training catalogue and their enrollments', () => {
    const sections = navigationForRole('INTERN');
    expect(sections.length).toBe(3);
    expect(sections[0].items[0].label).toBe('Tableau de bord');
    expect(labelsFor('INTERN')).toContain('Catalogue et sessions');
    expect(labelsFor('INTERN')).toContain('Inscriptions et validations');
    expect(labelsFor('INTERN')).toContain('Mon stage');
  });

  it('exposes scoped internship management to supervisors and HR', () => {
    expect(labelsFor('EMPLOYEE')).toContain('Gestion des stagiaires');
    expect(labelsFor('HR')).toContain('Gestion des stagiaires');
  });

  it('isolates the client training view', () => {
    expect(labelsFor('CLIENT')).toEqual(['Tableau de bord', 'Mes formations client']);
  });
});
