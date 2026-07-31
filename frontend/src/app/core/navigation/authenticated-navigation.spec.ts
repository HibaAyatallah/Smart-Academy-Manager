import { navigationForRole } from './authenticated-navigation';

const labelsFor = (role: Parameters<typeof navigationForRole>[0]) =>
  navigationForRole(role).flatMap((section) => section.items.map((item) => item.label));

describe('authenticated navigation', () => {
  it('reserves user management navigation for the Super Admin', () => {
    expect(labelsFor('SUPER_ADMIN')).toContain('Gestion des utilisateurs');
    expect(labelsFor('HR')).not.toContain('Gestion des utilisateurs');
  });

  it('limits candidate navigation to implemented candidate pages', () => {
    expect(labelsFor('CANDIDATE')).toEqual(['Tableau de bord']);
    expect(labelsFor('CANDIDATE')).not.toContain('Business Units');
  });

  it('gives BU Managers BU and training approval destinations', () => {
    expect(labelsFor('BU_MANAGER')).toEqual([
      'Tableau de bord', 'Besoins de ma BU', 'Membres de ma BU',
      'Catalogue et sessions', 'Inscriptions et validations',
      'Présences et certificats', 'Gestion des stagiaires',
    ]);
    expect(labelsFor('BU_MANAGER')).not.toContain('Business Units');
  });

  it('limits interns to the dashboard and their internship', () => {
    const sections = navigationForRole('INTERN');
    expect(sections.length).toBe(2);
    expect(sections[0].items[0].label).toBe('Tableau de bord');
    expect(labelsFor('INTERN')).toContain('Mon stage');
    expect(labelsFor('INTERN')).not.toContain('Projets');
    expect(labelsFor('INTERN')).not.toContain('Présences et certificats');
  });

  it('separates HR consultation from internship management', () => {
    expect(labelsFor('EMPLOYEE')).not.toContain('Gestion des stagiaires');
    expect(labelsFor('HR')).not.toContain('Gestion des stagiaires');
    expect(labelsFor('HR')).toContain('Stagiaires acceptés');
    expect(labelsFor('HR')).toContain('Collaborateurs par BU');
  });

  it('limits employees to their BU training entry point', () => {
    expect(labelsFor('EMPLOYEE')).toContain('Formations de ma BU');
    expect(labelsFor('EMPLOYEE')).not.toContain('Catalogue et sessions');
    expect(labelsFor('EMPLOYEE')).not.toContain('Inscriptions et validations');
    expect(labelsFor('EMPLOYEE')).not.toContain('Présences et certificats');
  });

  it('exposes project views only to project workflow roles', () => {
    for (const role of ['SUPER_ADMIN', 'EMPLOYEE'] as const) {
      expect(labelsFor(role)).toContain('Projets');
    }
    expect(labelsFor('HR')).not.toContain('Projets');
    expect(labelsFor('CANDIDATE')).not.toContain('Projets');
    expect(labelsFor('CLIENT')).not.toContain('Projets');
  });

  it('isolates the client training view', () => {
    expect(labelsFor('CLIENT')).toEqual(['Tableau de bord', 'Mes formations client']);
  });

  // The audit and report navigation test is removed as these sections no longer exist.
});
