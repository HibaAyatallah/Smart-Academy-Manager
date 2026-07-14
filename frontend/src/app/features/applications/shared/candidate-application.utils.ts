import {
  Application,
  ApplicationDocument,
  ApplicationDocumentType,
  ApplicationInterview,
  ApplicationStatus,
  ApplicationStatusHistory,
  EDUCATION_LEVEL_LABELS,
} from '../../../core/models/application.models';

export type CandidateApplicationStepState = 'done' | 'active' | 'pending' | 'rejected';

export function candidateApplicationStepState(
  application: Application,
  step: 0 | 1 | 2,
): CandidateApplicationStepState {
  if (application.status === 'REJECTED') {
    return 'rejected';
  }

  const currentStep = candidateApplicationStepIndex(application.status);
  if (currentStep > step) {
    return 'done';
  }
  return currentStep === step ? 'active' : 'pending';
}

export function candidateApplicationStepLabel(application: Application): string {
  return application.status === 'REJECTED'
    ? 'Refusée'
    : `T${candidateApplicationStepIndex(application.status)}`;
}

export function candidateApplicationTargetLabel(application: Application): string {
  return application.application_type === 'HIRING'
    ? 'Futur statut Collaborateur'
    : 'Futur statut Stagiaire';
}

export function candidateStudyLevelLabel(application: Application): string {
  if (application.candidate_profile.study_level === 'OTHER') {
    return application.candidate_profile.study_level_other || 'Autre';
  }
  return EDUCATION_LEVEL_LABELS[application.candidate_profile.study_level];
}

export function candidateHistoryDate(
  application: Application,
  statuses: readonly string[],
): string | null {
  return application.status_history.find((history) => statuses.includes(history.to_status))?.created_at ?? null;
}

export function candidateLatestInterview(application: Application): ApplicationInterview | null {
  return application.interviews[0] ?? null;
}

export function candidateDocument(
  application: Application,
  documentType: ApplicationDocumentType,
): ApplicationDocument | undefined {
  return application.documents.find((document) => document.document_type === documentType);
}

export function toSafeExternalUrl(url: string): string {
  if (!url) {
    return '';
  }
  return /^https?:\/\//i.test(url) ? url : `https://${url}`;
}

function candidateApplicationStepIndex(status: ApplicationStatus): number {
  if (status === 'ACCEPTED') {
    return 2;
  }
  if (['PRESELECTED', 'INTERVIEW_SCHEDULED', 'INTERVIEW_COMPLETED'].includes(status)) {
    return 1;
  }
  return 0;
}
