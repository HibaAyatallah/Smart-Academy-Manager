export interface ReportPoint {
  label: string;
  value: number;
}

export interface ActivityLog {
  id: number;
  action: string;
  resource_type: string;
  created_at: string;
  actor_name: string;
}

export interface ReportData {
  filters: { date_from: string; date_to: string; business_unit: string };
  cards: Record<string, number>;
  recent_activities?: ActivityLog[];
  recent_applications?: any[]; // For table
  series: Record<string, ReportPoint[]> & {
    applications_by_bu_status?: any[];
    workforce_by_bu?: any[];
    monthly_internships?: { label: string; upcoming: number; active: number; completed: number }[];
  };
  kpis: {
    average_project_progress: number;
    attendance_validation_rate: number;
    certificate_rate: number;
    active_memberships: number;
  };
}

export interface HRDashboardData {
  active_interns: number;
  interns_by_school: ReportPoint[];
  interns_by_bu: ReportPoint[];
  paid_interns: number;
  unpaid_interns: number;
  missing_documents: number;
  collaborators_by_bu: ReportPoint[];
  internship_timeline: {
    starts: { name: string; date: string; bu: string }[];
    ends: { name: string; date: string; bu: string }[];
  };
  trainings_overview: {
    active_trainings: number;
    upcoming_sessions: number;
    ongoing_sessions: number;
  };
}
