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
  filters: { date_from: string; date_to: string; business_unit: string; status: string; training_type: string };
  filter_options: {
    business_units: { id: number; name: string }[];
    application_statuses: { value: string; label: string }[];
    training_types: { value: string; label: string }[];
  };
  cards: Record<string, number>;
  insights: string[];
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

export interface BusinessUnitDashboardData {
  business_units: { id: number; name: string; code: string; description: string }[];
  counts: { needs: number; open_needs: number; collaborators: number; interns: number; active_interns: number };
  needs_by_status: ReportPoint[];
  interns_by_status: ReportPoint[];
  recent_needs: { id: number; title: string; status: string; priority: string; expected_date: string | null; business_unit_id: number; business_unit_name: string }[];
  recent_collaborators: { id: number; name: string; email: string; position: string; business_unit_name: string }[];
}
