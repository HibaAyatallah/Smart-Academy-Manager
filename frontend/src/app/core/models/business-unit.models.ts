

export enum NeedType {
  HIRING = 'HIRING',
  INTERNSHIP = 'INTERNSHIP',
  FREELANCE = 'FREELANCE',
}

export enum NeedRequiredLevel {
  JUNIOR = 'JUNIOR',
  MID = 'MID',
  SENIOR = 'SENIOR',
  EXPERT = 'EXPERT',
}

export enum NeedPriority {
  LOW = 'LOW',
  MEDIUM = 'MEDIUM',
  HIGH = 'HIGH',
  CRITICAL = 'CRITICAL',
}

export enum NeedStatus {
  DRAFT = 'DRAFT',
  OPEN = 'OPEN',
  IN_PROGRESS = 'IN_PROGRESS',
  FULFILLED = 'FULFILLED',
  CANCELLED = 'CANCELLED',
}

export interface BusinessUnit {
  id: number;
  name: string;
  code: string;
  description: string;
  manager: number;
  manager_email: string;
  manager_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface BusinessUnitMembership {
  id: number;
  business_unit: number;
  business_unit_name: string;
  user: number;
  user_email: string;
  user_name: string;
  position: string;
  joined_at: string;
  is_active: boolean;
}

export interface BusinessUnitNeed {
  id: number;
  business_unit: number;
  business_unit_name: string;
  title: string;
  description: string;
  need_type: NeedType;
  need_type_label: string;
  required_skills: string;
  required_level: NeedRequiredLevel;
  required_level_label: string;
  number_of_profiles: number;
  priority: NeedPriority;
  priority_label: string;
  expected_date: string | null;
  status: NeedStatus;
  status_label: string;
  created_by: number;
  created_by_email: string;
  created_at: string;
  updated_at: string;
}
