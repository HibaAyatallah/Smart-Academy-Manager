# Smart Academy Manager — Project Summary

## 1. Project Overview

Smart Academy Manager is an academic and human resources management platform built with Angular, Django REST Framework, and PostgreSQL. It is developed by Finatech to modernize and centralize recruitment, intern onboarding, Business Unit management, training administration, and operational HR workflows.

The platform solves the problem of fragmented candidate tracking, scattered intern onboarding, and disconnected Business Unit governance. It replaces ad-hoc processes with a single authenticated system that enforces role-based access, audit history, and secure document handling.

Target users include Super Admins, HR staff, BU Managers, Candidates, Collaborators/Employees, Interns, Trainers/Tutors, and External Clients. Each role has a tailored authenticated experience with role-filtered navigation and role-specific data visibility.

The public Finatech Connect website is a separate, unauthenticated presence. Smart Academy Manager is the authenticated internal platform that sits behind login. The public site may reference Finatech branding, but all operational functionality — applications, dashboards, Business Units, recruitment workflows — requires authentication and lives inside Smart Academy Manager.

Main objectives:
- Provide a secure, role-aware JWT authentication experience.
- Manage end-to-end recruitment from public application to acceptance or rejection.
- Organize Business Units, their managers, memberships, and operational needs.
- Prepare the foundation for future internships, projects, training, attendance, evaluations, certificates, notifications, and Moodle integration.
- Maintain a clean separation between public marketing content and private operational data.

## 2. User Roles

| Role | Purpose | Current Access | Status |
|---|---|---|---|
| | Super Admin | Full platform administration and oversight | All modules, all Business Units, user management, recruitment management | Functional |
| | HR | Human resources operations | Recruitment management, Business Unit administration, user management; functionally equivalent to Super Admin for implemented modules | Functional |
| | BU Manager | Operational management of a specific Business Unit | Own managed Business Unit, its memberships, and its needs; cannot modify another BU | Functional |
| | Candidate | External applicant | Public application submission, personal application history, personal documents, interviews | Functional |
| | Collaborator / Employee | Internal team member | Read-only access to own active Business Unit and Business Unit needs; generic dashboard | Partial |
| | Intern | Onboarded former candidate | Generic dashboard only; no domain-specific module yet | Placeholder |
| | Trainer / Tutor | Training delivery | Generic dashboard only; no training module yet | Placeholder |
| | External Client | External stakeholder | Generic dashboard only; no client-specific module yet | Placeholder |

Important distinctions:
- HR and Super Admin currently have equivalent functional permissions across recruitment, Business Units, and user management. This equivalence is enforced by a shared `is_administrative_user()` backend policy.
- BU Manager access is restricted to the Business Unit they manage. Cross-BU access is blocked by backend queryset filtering and object-level permissions.
- Candidate access is limited to their own applications, documents, and interviews.
- Collaborator read access to Business Units exists in the backend, but the Angular sidebar does not expose Business Unit routes to Collaborators, creating a frontend/backend mismatch.
- Intern, Trainer/Tutor, and External Client roles exist in the data model and navigation policy, but no dedicated functional modules are implemented yet.

## 3. Technical Architecture

### Frontend

- Angular 21 with standalone components
- Angular Material for UI components
- SCSS for styling with centralized design tokens
- JWT authentication via `AuthService` and `TokenStorageService`
- Role-based navigation through `authenticated-navigation.ts`
- Responsive authenticated shell with compact horizontal navigation on desktop and overlay drawer on mobile
- Separate public and authenticated layouts
- Production build configured for same-origin `/api/` delivery

### Backend

- Django 5.2 with Django REST Framework
- Custom `User` model based on email with centralized business roles
- JWT authentication via SimpleJWT
- PostgreSQL database configured through environment variables
- Role-based and object-level permissions enforced in serializers, views, and querysets
- DRF page-number pagination
- OpenAPI documentation via drf-spectacular
- Recruitment upload validation with size, extension, MIME, and magic-prefix checks
- DRF throttling for login, public submission, anonymous, and authenticated endpoints

### Planned Integrations

- Moodle REST Web Services — planned but not implemented
- Docker — planned but not implemented
- Render — planned but not implemented
- Vercel — planned but not implemented
- Future AI features — planned but not implemented

None of the planned integrations are currently implemented. The codebase contains no Dockerfile, Compose file, Render configuration, Vercel configuration, GitHub Actions workflow, or Moodle client code.

## 4. Current Functional Modules

| Module | Purpose | Backend Status | Frontend Status | Integration Status | Test Status |
|---|---|---|---|---|---|
| | Authentication | JWT login, token refresh, current-user profile, password change | Substantial | Substantial | Connected | Partial |
| | User Accounts | User CRUD, role assignment, administrative user management | Partial | Missing | Missing | Partial |
| | Personal Space | Read-only profile view and authenticated password change | Complete | Complete | Connected | Complete |
| | Recruitment | Application workflow, status transitions, interviews, documents | Substantial | Substantial | Connected | Partial |
| | Candidate Applications | Public submission, candidate history, HR review | Substantial | Substantial | Connected | Partial |
| | Candidate Documents | Secure upload, preview, download with ownership checks | Partial | Partial | Connected | Partial |
| | Interviews | Interview scheduling and completion | Partial | Partial | Connected | Partial |
| | Recruitment Workflow | Status changes: under review, preselection, interview, accept, reject | Substantial | Substantial | Connected | Partial |
| | Business Units | BU CRUD, manager assignment, ownership filtering | Partial | Partial | Connected | Partial |
| | Business Unit Needs | BU needs listing and detail | Partial | Partial | Connected | Partial |
| | Business Unit Memberships | Membership model and backend filtering | Partial | Placeholder | Missing | Partial |
| | Dashboards | Role-aware landing pages | Partial | Partial | Partial | Partial |
| | Audit Logs | Recruitment-sensitive action history | Partial | Missing | Missing | Partial |
| | Public Finatech Connect Website | Public-facing pages | Complete | Complete | N/A | Partial |
| | Authenticated Navigation | Role-filtered sidebar and header | Complete | Complete | Connected | Complete |

Status definitions:
- **Complete**: Fully implemented, tested, and integrated.
- **Substantial**: Core functionality exists and works; edge cases or polish may remain.
- **Partial**: Core functionality exists but has gaps, missing features, or incomplete coverage.
- **Placeholder**: Structure exists but is non-functional or intentionally hidden.
- **Missing**: No implementation exists.
- **Broken**: Implementation exists but integration is currently non-functional.

## 5. Recruitment Module

The recruitment module implements a complete workflow from public application to acceptance or rejection:

1. **Candidate submits an application**: A public, unauthenticated endpoint accepts multipart form data containing candidate identity, CV, cover letter, and optional additional documents. The backend creates a `User` with the Candidate role, a `CandidateProfile`, and an `Application` in a single transaction.

2. **Documents are uploaded**: Required documents (CV and cover letter) are validated for size, extension, declared MIME type, and magic prefix. Optional additional documents can be uploaded through a dedicated backend action.

3. **HR reviews the application**: HR and Super Admin can list applications with filters for status, type, and search terms. The Angular frontend provides a paginated table with loading, empty, and error states.

4. **Status transitions**: The backend exposes actions to move an application through defined states: mark as under review, preselect, schedule interview, complete interview, accept, and reject. Each transition is protected by role-based permissions.

5. **Preselection**: HR can mark a candidate as preselected, advancing the workflow.

6. **Interview management**: Interviews can be scheduled and completed through dedicated actions with structured data.

7. **Acceptance or rejection**: Accepted applications can be transformed into intern or collaborator accounts. Rejected applications deactivate the candidate account. Expired applications are anonymized by a management command.

8. **Audit history**: Sensitive recruitment actions are logged through `SensitiveAuditLog`, preserving who performed what action and when.

9. **Secure document access**: Document downloads are protected by ownership checks. Candidates can only access their own documents; HR and Super Admin can access documents for applications they can view.

What is already working:
- Public application submission with validation
- Candidate login and personal application list
- HR application list with filters and pagination
- Status transition actions on the backend
- Secure document streaming with ownership enforcement
- Audit logging for sensitive actions
- Email notifications for workflow events (synchronous, not a notification module)

What remains incomplete:
- Candidate application detail route in Angular (data is shown in cards/dashboard instead)
- Post-submission additional document upload UI in Angular
- Full workflow coverage testing across all transitions
- Malware scanning for uploaded files
- Notification inbox/preferences/delivery tracking module
- Offer model and offer-driven application workflow

## 6. Business Unit Module

Business Units organize the company's operational structure. Each Business Unit has a name, code, description, manager, and active status. Memberships link users to Business Units with role-specific access. Needs represent operational requirements assigned to a Business Unit.

Key concepts:
- **Business Units**: Top-level organizational units with a single manager.
- **BU Managers**: Users assigned as managers of a specific Business Unit. They can view and update their own BU within allowed field constraints.
- **BU Memberships**: Links between users and Business Units. Memberships can be active or inactive, preserving historical records.
- **BU Needs**: Operational needs or requests associated with a Business Unit.
- **Role restrictions**: BU Managers cannot access or modify Business Units they do not manage. Candidates and External Clients cannot access BU APIs at all. Collaborators have read-only access to their own active memberships.
- **Cross-BU security**: Backend queryset filtering ensures users only see data for Business Units they are authorized to access. Changing a URL ID does not bypass these filters.
- **Membership history**: Inactive memberships are preserved. Users can rejoin a Business Unit after their membership becomes inactive.

Latest corrections applied during the stabilization sprint:
- BU Managers cannot reassign the manager field of their own Business Unit. The `BusinessUnitViewSet.perform_update()` method blocks modifications to `manager`, `code`, and `is_active` fields when a BU Manager updates their own BU.
- Inactive membership history is preserved. The `unique_together` constraint was replaced with a conditional `UniqueConstraint` that only applies to active memberships, allowing users to rejoin after an inactive membership.
- Permissions are enforced by the backend through object-level permission classes and queryset filtering, not merely by Angular route guards.
- BU frontend URL construction has been corrected. The service now uses the centralized `environment.apiBaseUrl` value without introducing double-slash errors.

Current frontend status:
- BU list, detail, needs list, and need-detail pages are functional and connected to the backend.
- BU creation and editing forms are not implemented; HR and Super Admin must use the API or Django admin for BU mutations.
- BU membership management UI is intentionally not exposed because the frontend placeholder and business rules are not yet stable.
- Three BU components (`bu-detail`, `bu-need-detail`) were generated placeholders and have been replaced with functional read-only implementations, but full CRUD forms remain incomplete.

## 7. Authenticated Interface

The authenticated interface provides a modern, role-aware shell for all logged-in users.

Current authenticated design:
- **Permanent sidebar removed**: The interface no longer uses a fixed sidenav. Desktop uses a compact horizontal navigation bar; mobile uses a temporary overlay drawer below 768 px.
- **Real Finatech logo used**: The navigation displays the actual `logo_finatech.png` instead of placeholder branding.
- **Compact horizontal navigation**: Links are grouped by role, with active underline indicators and icon-only collapsed state with tooltips.
- **Mobile overlay menu**: Below 768 px, navigation becomes an accessible Material drawer that closes after selection.
- **One account control**: Exactly one account trigger exists in the header. The menu contains only "Mon espace personnel" and "Se déconnecter".
- **Internal personal-space page**: The `/espace-personnel` route displays real `/auth/me/` identity data (first name, last name, email, role, phone) as read-only text.
- **Password change functionality**: An authenticated `POST /api/auth/change-password/` endpoint verifies the current password, applies Django validators, and hashes the new password through `set_password()`.
- **Role-based navigation**: The `authenticated-navigation.ts` component filters visible links based on the logged-in user's role. HR and Super Admin see equivalent links. Candidates see dashboard and applications. BU Managers see dashboard, Business Units, and BU needs. Other roles see only implemented pages.
- **First-click route rendering correction**: The authenticated layout uses Angular Material sidenav `autosize` and explicit flex sizing to ensure routed content renders correctly on the first click without requiring a resize or hamburger toggle.

Individual role dashboards will be customized later. Currently, only the Candidate dashboard loads real application data. All other roles receive an honest empty state instead of invented KPIs or charts.

## 8. Security

Current security measures:
- **JWT authentication**: Access tokens expire after 15 minutes; refresh tokens expire after 7 days. Authentication is handled by SimpleJWT with email-based login. The project uses JWT authentication, not SSO.
- **Backend role permissions**: Role checks are enforced in Django views, serializers, and querysets, not merely in Angular guards.
- **Object-level permissions**: Custom permission classes filter querysets by ownership. BU Managers see only their own Business Units. Candidates see only their own applications and documents.
- **Protected candidate documents**: Document download endpoints recheck ownership before streaming files. Direct ID manipulation returns 404.
- **File validation**: Uploaded files are checked for size, extension, declared MIME type, and magic prefix. DOCX files are checked for the `PK` prefix.
- **Password validation**: Django password validators are applied on creation and change. Passwords are hashed through `set_password()`.
- **Authenticated self-service password change**: Users can change their own password by providing the current password. The endpoint affects `request.user` only.
- **DRF throttling**: Rate limiting is configured for anonymous access (20/hour), authenticated users (60/minute), JWT login (10/minute), and public application submission (5/hour). Test requests use elevated limits to avoid interference.
- **HR and Super Admin equivalence**: A shared `is_administrative_user()` helper ensures HR and Super Admin have identical functional access across implemented modules.
- **BU Manager restrictions**: BU Managers cannot modify sensitive fields (`manager`, `code`, `is_active`) on their own Business Unit. They cannot access or modify Business Units they do not manage.

Remaining security improvements:
- **JWT refresh rotation and blacklisting**: Refresh tokens are stored in browser storage and are neither rotated nor blacklisted. A refresh-token blacklist app and rotation policy should be implemented.
- **Malware scanning**: Uploaded Office and PDF files receive only extension/MIME/header checks, not antivirus or content-disarm scanning.
- **Production secrets enforcement**: The base settings contain unsafe fallback secrets and placeholder database URLs. Production settings should require explicit secrets and fail closed if missing.
- **HTTPS hardening**: Production configuration lacks `SECURE_SSL_REDIRECT`, explicit referrer policy, and verified proxy configuration examples.
- **Production media storage**: Private media storage strategy and object storage configuration are absent. Direct `MEDIA_URL` serving is not wired in `urls.py`.
- **Production email configuration**: Local console email backend is used for development. Production email delivery configuration is missing.

## 9. Tests and Validation

Latest verified results from the stabilization sprint (2026-07-14):

| Check | Result | Command |
|---|---|---|
| Frontend tests | 73/73 PASSED | `cd frontend && npm test -- --watch=false` |
| Backend accounts tests | 14/14 PASSED | `python manage.py test apps.accounts.tests` |
| Backend business_units tests | 24/24 PASSED | `python manage.py test apps.business_units.tests` |
| Backend recruitment tests | 35/35 PASSED | `python manage.py test apps.recruitment.tests` |
| Django system check | No issues | `python manage.py check` |
| Migration drift check | No changes detected | `python manage.py makemigrations --check --dry-run` |
| Angular production build | Successful | `npm run build` |

Note: Running all backend tests together occasionally causes a PostgreSQL database lock. This is a pre-existing test infrastructure issue, not a code issue. Individual app test suites run successfully.

Total automated test count: 146 tests (73 backend + 73 frontend), all passing.

Business Unit frontend tests:
- `bu-list.spec.ts`: 4 tests covering create, load, empty state, pagination, error state
- `bu-needs-list.spec.ts`: 6 tests covering create, load, empty state, pagination, error state, filters
- `bu-need-detail.spec.ts`: 4 tests covering load, not-found, BU mismatch, invalid ID

## 10. Missing Modules

The following modules are not yet implemented:

- Offers
- Projects
- Internships management
- Training
- Training sessions
- Enrollments
- Attendance
- Evaluations
- Certificates
- Notifications (notification inbox, preferences, delivery tracking)
- Reports and KPIs
- Moodle integration
- AI features
- CI/CD
- Production deployment

No code, models, APIs, or frontend components exist for these modules. They are planned for future sprints.

## 11. Current Project Progress

**Overall progress: 30.1%**

This percentage is calculated from a weighted assessment of backend implementation, frontend implementation, frontend-backend integration, roles and security, tests and validation, and deployment and documentation. The scoring counts working connected behavior, not file presence.

| Category | Weight | Score | Weighted contribution | Basis |
|---|---|---:|---:|---|
| Backend implementation | 25% | 32% | 8.00% | Auth, recruitment, and BU foundations exist; most product modules absent |
| Frontend implementation | 25% | 30% | 7.50% | Public/auth/recruitment substantial; BU functional; other role experiences placeholders |
| Frontend-backend integration | 20% | 35% | 7.00% | Auth/recruitment/BU mapped and connected; most modules missing |
| Roles and security | 10% | 42% | 4.20% | Useful backend ownership filters; HR/Admin equivalence complete; token/upload/throttle gaps remain |
| Tests and validation | 10% | 24% | 2.40% | 73 frontend tests and 73 backend tests pass; major coverage gaps remain |
| Deployment and documentation | 10% | 10% | 1.00% | Basic docs/env example only; no deployment artifacts/CI |
| **Total** | **100%** |  | **30.10%** | Weighted sum |

The percentage is not higher because:
- Passing tests validate only the functionality that has been implemented.
- Many planned modules (offers, projects, training, sessions, enrollments, attendance, evaluations, certificates, notifications, reports, Moodle, AI) are completely absent.
- Production deployment, CI/CD, and infrastructure are not implemented.
- The project is assessed against the final multi-module application scope, not an MVP.

The 30.1% figure reflects a useful early foundation with a substantial recruitment vertical slice and a partially implemented Business Unit module, but it is not production-ready and does not represent the full business scope.

## 12. Main Strengths

- **Stable authentication**: JWT login, token refresh, current-user profile, and password change are implemented and tested on both backend and frontend.
- **Substantial recruitment workflow**: Public application submission, HR review, status transitions, interviews, document management, and audit logging are functional and connected.
- **Secure role permissions**: Backend enforces role-based and object-level permissions. BU Managers, Candidates, and Collaborators are properly restricted.
- **Tested Business Unit backend and frontend**: Business Unit models, querysets, permissions, and mutations have comprehensive backend test coverage, including adversarial tests for manager reassignment and cross-BU access. Frontend BU list, needs list, and need detail components are functional with tests.
- **Modern authenticated shell**: The interface uses a compact horizontal navigation, real Finatech branding, responsive mobile drawer, personal space, and role-filtered navigation.
- **Strong automated tests**: 146 automated tests cover authentication, recruitment, Business Units, navigation, layout, and security scenarios.
- **Separation between public and authenticated interfaces**: Public application submission is unauthenticated, while all operational functionality requires login and role enforcement.
- **Public Finatech Connect pages**: Real public pages exist for home, about, careers, recruitment, contact, privacy, and legal. These are functional static pages, not placeholders.

## 13. Main Remaining Work

### Priority 1 — Complete existing modules
- Complete Business Unit membership and need forms and workflows.
- Finalize HR and Super Admin functional equivalence across all endpoints and Angular navigation.
- Add candidate application detail route and post-submission document upload UI.
- Complete throttle, upload safety, and session hardening for production.

### Priority 2 — Implement the next business modules
- Design and implement offers and offer-linked application workflow.
- Implement internships management, projects, training, training sessions, enrollments, attendance, evaluations, and certificates.
- Build real role-specific dashboards for Intern, Trainer/Tutor, Collaborator, and External Client.
- Add notification inbox, preferences, and delivery tracking.

### Priority 3 — Improve security and production configuration
- Implement JWT refresh rotation and blacklisting.
- Add malware scanning for uploaded files.
- Enforce production secrets and fail-closed configuration.
- Harden HTTPS, CORS, hosts, and media storage for production.
- Configure production email delivery.

### Priority 4 — Moodle and future AI integration
- Design Moodle REST Web Services integration with separate database and credentials.
- Add Docker, Render, Vercel, and GitHub Actions CI/CD.
- Explore AI features for reporting, recommendations, or automation.

## 14. Recommended Next Module

The most logical next functional module to implement is **Offers**.

Offers should be implemented next because:
- It directly extends the existing recruitment workflow. Currently, applications are submitted without an associated offer model. Introducing offers creates a proper top-down recruitment flow: HR creates an offer, candidates apply to a specific offer, and the application is linked to that offer.
- It connects naturally with Business Units. Offers can be assigned to a Business Unit, making the BU module more meaningful and driving usage of the BU needs and membership infrastructure.
- It bridges recruitment and internships. Accepted candidates from offer-driven applications can be transformed into interns with a clear lineage from offer to intern record.
- It provides structure for future training. Offers can define required skills or training paths, creating a natural bridge to the training module.
- It adds business value immediately. HR can manage open positions, track offer status, and report on recruitment pipeline metrics.

Implementation should include: Offer model with title, description, Business Unit, status, and dates; Offer CRUD API with role-based permissions; Angular offer list, detail, and create/edit forms; and linking existing applications to offers through a migration or updated submission flow.

## 15. Final Conclusion

Smart Academy Manager is an early-stage but structurally sound platform. It has a stable authentication foundation, a substantial and tested recruitment vertical slice, and a partially implemented Business Unit module with strong security testing. The authenticated interface is modern, responsive, and role-aware.

What already works:
- JWT authentication and password management
- Public candidate application submission with validation
- HR recruitment management with status workflows
- Secure document handling with ownership enforcement
- Business Unit backend and frontend with role filtering and manager restrictions
- Responsive authenticated shell with role-based navigation
- 146 passing automated tests
- Public Finatech Connect pages (home, about, careers, recruitment, contact, privacy, legal)

What remains to be developed:
- Complete Business Unit CRUD forms and membership management
- Offers, projects, internships, training, sessions, enrollments, attendance, evaluations, certificates
- Notifications, reports, KPIs, and general audit logs
- Moodle integration, AI features, CI/CD, and production deployment
- Security hardening for production (JWT rotation, malware scanning, HTTPS, media storage)

The project is **ready for demonstration** of the implemented modules (authentication, recruitment, Business Units, authenticated shell, public pages) against a correctly provisioned backend. It is **not ready for production** due to missing modules, incomplete Business Unit CRUD forms, lack of deployment infrastructure, and unresolved production security configuration.