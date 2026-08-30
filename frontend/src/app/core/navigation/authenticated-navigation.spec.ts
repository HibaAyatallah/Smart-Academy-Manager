import { navigationForRole } from './authenticated-navigation';

const labelsFor = (role: Parameters<typeof navigationForRole>[0]) =>
  navigationForRole(role).flatMap((section) => section.items.map((item) => item.label));

const iconFor = (role: Parameters<typeof navigationForRole>[0], label: string) =>
  navigationForRole(role).flatMap((section) => section.items).find((item) => item.label === label)?.icon;

describe('authenticated navigation', () => {
  it('reserves user management navigation for the Super Admin', () => {
    expect(labelsFor('SUPER_ADMIN')).toContain('Gestion des utilisateurs');
    expect(labelsFor('HR')).not.toContain('Gestion des utilisateurs');
  });

  it('shows only the retained administration workflow to Super Admin', () => {
    const labels = labelsFor('SUPER_ADMIN');
    expect(labels).toContain('Catalogue des formations');
    expect(labels).toContain('Personnes inscrites');
    expect(labels).not.toContain('Catalogue et sessions');
    expect(labels).not.toContain('Inscriptions et validations');
    expect(labels).not.toContain('Présences et certificats');
  });

  it('limits candidate navigation to personal authenticated destinations', () => {
    expect(labelsFor('CANDIDATE')).toEqual(['Tableau de bord', 'Mon CV']);
    expect(labelsFor('CANDIDATE')).not.toContain('Mes candidatures');
    expect(labelsFor('CANDIDATE')).not.toContain('Business Units');
  });

  it('limits BU Managers to their operational BU destinations', () => {
    expect(labelsFor('BU_MANAGER')).toEqual([
      'Tableau de bord', 'Besoins de ma BU', 'Membres de ma BU',
      'Inscriptions et validations', 'Présences et certificats',
      'Gestion des stagiaires',
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

  it('does not expose notifications or an empty tools section to any role', () => {
    for (const role of ['SUPER_ADMIN','HR','BU_MANAGER','TRAINER_TUTOR','EMPLOYEE','INTERN','CANDIDATE','CLIENT'] as const) {
      const navigation = navigationForRole(role);
      expect(labelsFor(role)).not.toContain('Notifications');
      expect(navigation.some((section) => section.label === 'Outils')).toBeFalse();
      expect(navigation.every((section) => section.items.length > 0)).toBeTrue();
    }
  });

  it('does not expose reports and audit logs in role navigation', () => {
    expect(labelsFor('SUPER_ADMIN')).not.toContain('Rapports & KPI');
    expect(labelsFor('SUPER_ADMIN')).not.toContain('Journaux d’audit');
    for (const role of ['HR','BU_MANAGER','TRAINER_TUTOR','EMPLOYEE','INTERN','CANDIDATE','CLIENT'] as const) {
      expect(labelsFor(role)).not.toContain('Rapports & KPI');
      expect(labelsFor(role)).not.toContain('Journaux d’audit');
    }
  });

  it('uses consistent icons for shared user-space concepts', () => {
    expect(iconFor('SUPER_ADMIN', 'Gestion des stagiaires')).toBe('badge');
    expect(iconFor('HR', 'Stagiaires acceptés')).toBe('badge');
    expect(iconFor('INTERN', 'Mon stage')).toBe('badge');
    expect(iconFor('TRAINER_TUTOR', 'Catalogue et sessions')).toBe('school');
    expect(iconFor('TRAINER_TUTOR', 'Présences et certificats')).toBe('card_membership');
  });
});
