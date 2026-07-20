export type NotificationCategory='APPROVAL'|'ASSIGNMENT'|'SESSION'|'EVALUATION'|'DOCUMENT'|'CERTIFICATE';
export interface AppNotification{id:number;category:NotificationCategory;title:string;message:string;link:string;target_type:string;target_id:string;is_read:boolean;read_at:string|null;created_at:string;}
export interface NotificationPreferences{approvals:boolean;assignments:boolean;sessions:boolean;evaluations:boolean;documents:boolean;certificates:boolean;updated_at?:string;}
export interface AuditLog{id:number;actor_email:string;method:string;path:string;action:string;target_type:string;target_id:string;status_code:number;ip_address:string|null;metadata:Record<string,unknown>;created_at:string;}
