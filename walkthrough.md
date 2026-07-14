# Smart Academy Manager — Codex Technical Audit

Audit date: 2026-07-14. Evidence base: repository contents and working tree at `main` / `b169361`. “Verified” means traced in source and, where stated, executed. It does not mean production-tested. No feature code was changed during this audit.

# Stabilization Sprint — 2026-07-14

## 1. Stabilization Summary

The previously untracked recruitment, Business Unit, and Angular source has been reviewed and is now safely staged without committing or pushing. The backend virtual environment was rebuilt from the repository requirements, the missing verified `django-filter` dependency was added, and full Django validation now executes successfully against PostgreSQL.

HR and Super Admin now use one centralized administrative-capability helper across users, recruitment, and Business Units. BU Manager mutation boundaries were tightened. Angular production no longer targets localhost, BU API URLs no longer contain a double slash, read-only BU and need details are functional, and the unfinished membership route is no longer exposed.

Recruitment implementation and tests were preserved. Remaining limitations are listed in section 10 below.

## 2. Git Safety Review

- Staged source: tracked documentation/configuration changes; Django accounts/recruitment/BU applications; migrations; backend and frontend tests; Angular source, assets, package manifests, and this report.
- Intentionally ignored: `backend/.env`, `backend/.venv/`, `backend/media/`, Python caches, `frontend/node_modules/`, `frontend/.angular/`, `frontend/dist/`, coverage output, SQLite databases, and npm debug logs.
- `.gitignore` was tightened with `*.sqlite3` and `npm-debug.log*`; `.env.example` remains explicitly trackable.
- No deleted tracked file existed and no test was restored or deleted. Git history contains no prior Angular tests to restore.
- No secret, local database, uploaded candidate file, virtual-environment file, dependency directory, or build output is staged.
- No commit or push was created.

## 3. Backend Environment

- Python: 3.12.13.
- Django: 5.2.16.
- Dependency source: `backend/requirements/local.txt` → `backend/requirements/base.txt`.
- Virtual environment: `backend/.venv` (ignored by Git).
- The pre-existing environment was broken because its interpreter path no longer existed; it was safely recreated.
- Verified missing dependency: `django-filter` was imported by `backend/apps/business_units/views.py` but absent from requirements. `django-filter>=25.1,<26.0` was added and `django_filters` registered in installed apps.
- `python -m pip check`: `No broken requirements found.`

## 4. Backend Validation Results

Final run from `backend/` using `.venv/Scripts/python.exe`:

- `python manage.py check`: exit 0; `System check identified no issues (0 silenced).`
- `python manage.py makemigrations --check --dry-run`: exit 0; `No changes detected`.
- `python manage.py showmigrations`: exit 0; all accounts, admin, auth, business_units, contenttypes, recruitment, and sessions migrations shown as applied. Recruitment is applied through `0003`; BU through `0001`.
- `python manage.py test --noinput`: exit 0; 56 tests found, 56 passed in 83.501 seconds; PostgreSQL test database created and destroyed successfully.

## 5. HR and Super Admin Correction

Affected files include `backend/apps/accounts/roles.py`, accounts permissions/serializers/views/tests, recruitment permissions, and BU permissions/serializers/views/tests.

- Added `ADMINISTRATIVE_ROLES` and `is_administrative_user()` as the shared backend policy.
- HR and Super Admin now receive the same user queryset and may assign the same role values through the API.
- Recruitment and BU administrative checks delegate to the same helper.
- Existing role strings remain unchanged for stored-data and Angular compatibility.
- BU Managers cannot create/delete BUs, reassign their own BU, mutate another BU, or create needs for another BU.
- New tests compare HR and Super Admin user-list and BU-list responses and exercise BU Manager forbidden mutations. All backend tests pass.
- Django Admin still uses Django's `is_staff`/model-permission mechanism; role equivalence applies to the implemented application APIs and does not silently grant admin-site login to every HR/Super Admin role record.

## 6. Angular Production Configuration

Previously, `frontend/src/environments/environment.ts` permanently used `http://127.0.0.1:8000/api/` in production. Production now uses the same-origin `/api/` contract, while `environment.development.ts` retains local development configuration. Services consume the centralized environment value and contain no credentials.

The remaining deployment requirement is to configure the eventual HTTPS host/reverse proxy so `/api/` reaches Django. No live domain was invented. This is documented in `frontend/README.md`.

## 7. Business Unit Frontend Status

| Component | Previous state | Current state | Route | API | Tests |
|---|---|---|---|---|---|
| `bu-list` | Partial/broken URL and bad create link | Usable paginated list with loading/empty/error handling | Exposed | Correct `GET /api/business-units/` | Success, empty, error, pagination |
| `bu-needs-list` | Partial/broken URL | Usable paginated list; existing states preserved | Exposed | Correct `GET /api/business-unit-needs/` | Service endpoint/pagination covered |
| `bu-detail` | Empty placeholder | Read-only backend detail with loading/403/404/error states | Exposed | Correct detail endpoint | Load and scoped 404 |
| `bu-need-detail` | Empty placeholder | Read-only need detail; verifies route BU matches response BU | Exposed | Correct need detail endpoint | Load and BU mismatch |
| `bu-members` | Empty placeholder | Source preserved, route removed | Not exposed | Membership service preserved; no UI calls | Route absence asserted |

The nonexistent `/business-units/new` link was removed. Parent route access remains restricted to `SUPER_ADMIN`, `HR`, and `BU_MANAGER`. Django queryset tests prove BU Managers see only their own BUs and cannot modify another manager's object by changing an ID.

## 8. Files Created, Modified, Restored, and Staged

Important creations:

- `backend/apps/accounts/roles.py`: centralized administrative role policy.
- BU frontend service/component/route specs: meaningful API, state, pagination, ownership, and route-exposure tests.
- Real `bu-detail` and `bu-need-detail` presentations replacing generated placeholder output.

Important modifications:

- `.gitignore`: narrow SQLite/npm-log exclusions.
- backend requirements/settings: verified `django-filter` dependency.
- accounts/recruitment/BU permissions and tests: role equivalence and object-mutation hardening.
- Angular production environment/service/routes/README: deployment-safe API base, corrected endpoints, and removal of unfinished routes/links.

Restored files: none were deleted in Git. Existing tests and recruitment functionality remain present. All reviewed source and documentation changes are staged; ignored runtime/generated files are not.

## 9. Frontend Validation Results

- `npm run`: scripts available are `start`, `test`, `ng`, and `build`; no lint script exists.
- `npm run build`: passed; production bundle generated successfully, initial raw total 421.28 kB.
- `npm test -- --watch=false`: final run passed, `TOTAL: 44 SUCCESS` in Chrome 147.
- Lint: not run because no lint script is configured.

## 10. Remaining Blocking Issues

- The same-origin production `/api/` route still requires real hosting/reverse-proxy configuration before deployment.
- BU membership management remains intentionally unexposed because its placeholder frontend and membership business rules are not stable.
- The BU creation/editing UI is intentionally not implemented in this stabilization sprint; HR/Super Admin can currently use the verified API/admin paths, while Angular provides required list/detail flows.
- Existing repository-wide mojibake/encoding defects remain outside the narrow stabilization changes and should be corrected in a dedicated quality pass.
- Production upload malware scanning, JWT refresh-token hardening, and public endpoint throttling identified in the audit remain unresolved security work.

## 1. Executive Summary

**Weighted overall progress: 30.1%.** This is an early, non-production-ready application with a useful authentication foundation, a substantial recruitment vertical slice, and a partially started Business Unit (BU) backend. It is not the final application described by the business scope.

Strongest areas are JWT login/current-user handling (`backend/apps/accounts`, `frontend/src/app/core/services/auth.service.ts`), recruitment data/workflow APIs (`backend/apps/recruitment`), recruitment Angular screens (`frontend/src/app/features/applications`), and backend ownership filtering for candidate documents.

Largest gaps are offers, projects, training, sessions, enrollment, attendance, evaluations, certificates, notifications, Moodle, reports/KPIs, general audit logs, deployment, and most role-specific workspaces. The BU frontend has only two substantive list components; three routed screens are generated placeholders.

Main risks:

- the entire frontend, recruitment app, and BU app are untracked and therefore absent from the committed product;
- production Angular points to localhost;
- BU Angular services construct double-slash API paths and a list links to a missing creation route;
- BU model validation is not enforced on ordinary ORM saves, and reassignment/update validation is incomplete;
- HR and Super Admin are not functionally identical in user-management query/serializer rules;
- JWT refresh tokens are browser-stored and are neither rotated nor blacklisted;
- public recruitment has no throttling/rate limiting;
- uploaded Office files receive only extension/MIME/header checks, not malware scanning;
- backend validation could not run because Django is not installed in the available Python environment.

Current demonstrability: the Angular application builds and its 31 tests pass, and public/auth/recruitment screens can be demonstrated against a correctly provisioned backend. BU list pages are expected to fail integration until URL construction is corrected. Most role dashboards are generic profile pages. Production readiness is **No**.

## 2. Git and Repository State

Commands executed: `git status`, `git diff --stat`, `git diff`, and `git log --oneline -10`.

- Branch: `main`, aligned with `origin/main`.
- Only commit: `b169361 Initialisation du backend Smart Academy Manager`.
- Modified tracked files: `.gitignore`, `README.md`, `backend/.env.example`, `backend/README.md`, `backend/apps/accounts/permissions.py`, `backend/config/settings/base.py`, `backend/config/urls.py`, `docs/api.md`, `docs/backend-setup.md`.
- Untracked: all of `frontend/`, `backend/apps/recruitment/`, and `backend/apps/business_units/`.
- Deleted tracked files: none. No tracked Angular specs existed in `HEAD`; therefore there is no Git evidence that Angular tests were deleted. The current untracked frontend contains nine spec files and 31 tests.
- Ignored generated content observed: `frontend/node_modules/`, `frontend/.angular/`, `frontend/dist/`, Python `__pycache__/`. Ignore rules cover these. `coverage/` and `*.tsbuildinfo` were newly added to `.gitignore`.
- The modified accounts permission makes HR pass the nominal “super admin” permission and allows HR object management, while `UserViewSet` and serializers still distinguish HR from Super Admin. This is unfinished harmonization, not a completed HR/Super Admin equivalence.
- Recent BU work is unfinished: `bu-detail`, `bu-members`, and `bu-need-detail` are generated placeholders; no BU frontend specs exist.
- The working tree contains mojibake (for example `CrÃ©ation`) across newly added Python/Angular files, indicating an encoding/tooling quality issue.

No valid work was reverted. `walkthrough.md` is the only audit-created file.

## 3. Architecture Overview

### Backend

Django/DRF is split into `accounts`, `recruitment`, `business_units`, and an empty `core` app. `config/settings/base.py` configures PostgreSQL via `DATABASE_URL`, JWT authentication, DRF page-number pagination, CORS, OpenAPI, static/media paths, and recruitment upload limits. `local.py` uses console email; `production.py` enables several HTTPS cookie/HSTS settings. Routes are registered in `config/urls.py`.

There are no signals. Recruitment domain operations live in `backend/apps/recruitment/services.py`; upload checks are in `validators.py`; retention anonymization is a management command. BU logic is mostly in serializers/querysets/permissions.

### Frontend

Angular 21 standalone components use Angular Material and SCSS. `app.routes.ts` separates public, auth, and authenticated layouts. JWT state is handled by `AuthService`, `TokenStorageService`, functional guards, and `authInterceptor`. Recruitment is the only broad functional frontend. BU lists are started. Other roles share a generic dashboard.

### Database and authentication

The configured database is PostgreSQL. No Moodle database or Moodle client exists, so database separation cannot yet be runtime-verified. Authentication is Django email/password plus SimpleJWT; no SSO or AI code was found. Django passwords remain hashed through `UserManager`; no Moodle password-copy code exists.

### Infrastructure

No Dockerfile, Compose file, Render configuration, Vercel configuration, or GitHub Actions workflow exists. Documentation is limited to root/backend READMEs and `docs/api.md`, `docs/backend-setup.md`, `docs/git-github.md`. There is no full deployment/runbook or architecture decision record.

## 4. Module Status Matrix

| Module | Backend | Frontend | Integration | Tests | Final status | Main remaining task / evidence |
|---|---|---|---|---|---|---|
| Authentication | Partial | Partial | Connected | Partial | Partial | Refresh/logout hardening; `accounts/*`, `core/services/auth.service.ts` |
| Users | Partial | Missing | Missing | Partial | Partial | No Angular user administration; `accounts/views.py` |
| Roles/permissions | Partial | Partial | Partial | Weak | Partial | Reconcile HR/Super Admin and complete role/object matrix |
| Candidate profiles | Partial | Partial | Connected | Partial | Partial | Recruitment-bound only; no editable profile page |
| Recruitment offers | Missing | Missing | Missing | Missing | Missing | No offer model/API/page |
| Applications | Substantial/Partial | Substantial/Partial | Connected | Partial | Partial | Candidate detail route, notifications, full workflow coverage |
| Candidate documents | Partial | Partial | Connected | Partial | Partial | Malware scanning, stronger content checks, upload UI after submission |
| Business Units | Partial | Partial | Broken | Partial | Broken | Fix URL construction; implement details/forms |
| BU memberships | Partial | Placeholder | Missing | Weak | Partial | Implement UI and validate eligible member roles |
| BU needs | Partial | Partial | Broken | Weak | Partial | Implement create/detail/edit; correct paths |
| Interns | Placeholder | Missing | Missing | Weak | Placeholder | Only `InternProfile` conversion record exists |
| Projects | Missing | Missing | Missing | Missing | Missing | Design/implement after core stabilization |
| Training | Missing | Missing | Missing | Missing | Missing | No model/API/UI |
| Training sessions | Missing | Missing | Missing | Missing | Missing | No implementation |
| Enrollments | Missing | Missing | Missing | Missing | Missing | No implementation |
| Attendance | Missing | Missing | Missing | Missing | Missing | No implementation |
| Evaluations | Missing | Missing | Missing | Missing | Missing | No implementation |
| Certificates | Missing | Missing | Missing | Missing | Missing | No implementation |
| Dashboards | Missing | Placeholder | Partial | Weak | Placeholder | Candidate data only; all other roles show generic profile |
| Notifications | Missing | Missing | Missing | Missing | Missing | Emails are synchronous workflow helpers, not notifications module |
| Moodle integration | Missing | Missing | Missing | Missing | Missing/planned | Preserve separate DBs and credentials when designed |
| Reports/KPIs | Missing | Missing | Missing | Missing | Missing | No metrics endpoints or widgets |
| Audit logs | Recruitment-only | Missing | Missing | Weak | Partial | `SensitiveAuditLog` covers selected recruitment actions only |
| Administration | Partial | Missing | Missing | Weak | Partial | Django admin registrations exist; no application admin frontend |

Files existing alone were not treated as completion.

## 5. Frontend-Backend API Mapping

Base frontend URL comes from `frontend/src/environments/environment*.ts`. Application endpoints map through the DRF router in `backend/config/urls.py`; BU endpoints map through `backend/apps/business_units/urls.py`.

| Angular file / method | HTTP and frontend URL | Django view / serializer / permission | Payload → response | Status |
|---|---|---|---|---|
| `auth.service.ts` `login` | POST `api/auth/token/` | `SmartAcademyTokenObtainPairView`; JWT serializer; public token view | email/password → access/refresh | Connected |
| `auth.service.ts` `loadProfile` | GET `api/auth/me/` | `MeAPIView`; `MeSerializer`; authenticated | none → user profile | Connected |
| `auth.service.ts` `refreshAccessToken` | POST `api/auth/token/refresh/` | SimpleJWT `TokenRefreshView` | refresh → access | Connected |
| `application.service.ts` `submitPublicApplication` | POST `api/applications/public-submit/` | `ApplicationViewSet.public_submit`; `PublicApplicationCreateSerializer`; AllowAny | multipart candidate + documents → application | Connected |
| `getMyApplications` | GET `api/applications/mine/?page=` | `ApplicationViewSet.mine`; `ApplicationSerializer`; participant | none → DRF page | Connected |
| `listApplications` | GET `api/applications/?application_type=&status=&search=&page=` | `ApplicationViewSet.list`; `ApplicationSerializer`; participant/query filtering | filters → DRF page | Connected |
| `getApplication` | GET `api/applications/{id}/` | `ApplicationViewSet.retrieve`; `ApplicationSerializer`; participant/object filter | none → application | Connected for HR/Admin; candidate route absent |
| `downloadDocument` | GET serializer-provided `api/application-documents/{id}/download/` | `ApplicationDocumentViewSet.download`; ownership filter | none → file stream | Connected |
| workflow methods | POST `applications/{id}/{mark-under-review,preselect,schedule-interview,complete-interview,accept,reject}/` | matching actions; transition/schedule serializers; manager permission | `{}`, schedule fields, or reason → application | Connected |
| `business-unit.service.ts` BU CRUD | GET/POST/PATCH/DELETE `api//business-units/...` | `BusinessUnitViewSet`; `BusinessUnitSerializer`; `CanViewBUData` | BU fields ↔ BU | **Broken: extra slash** |
| membership CRUD | GET/POST/PATCH/DELETE `api//business-unit-memberships/...` | `BusinessUnitMembershipViewSet`; membership serializer; manager permission | membership fields ↔ membership | **Broken: extra slash** |
| need CRUD | GET/POST/PATCH/DELETE `api//business-unit-needs/...` | `BusinessUnitNeedViewSet`; need serializer; `CanViewBUData` | need fields ↔ need | **Broken: extra slash** |

Additional findings:

- `environment.apiBaseUrl` already ends in `/`; `BusinessUnitService` adds another leading `/`. Application/Auth services concatenate correctly.
- Backend endpoints unused by Angular: user CRUD, token verify, application history as a direct request, add-document, cancel, application-document list/detail, and interview CRUD.
- Angular BU create/update/delete service methods have no implemented forms. `/business-units/new` is linked but route matching treats `new` as `:id`, loading an empty detail placeholder.
- Angular pagination assumes DRF page size 20 and correctly sends `page`; BU components type responses as `any`, weakening interface verification.
- No global handling tailored to 403/404/validation errors exists in the interceptor; recruitment components handle some errors locally. BU errors collapse to an HTTP-status message.
- The public contact form explicitly shows a local informational result and makes no API request (`pages/public/contact/contact.component.ts`).

## 6. Role and Permission Matrix

| Role | Sidebar / Angular routes | Django access actually implemented | Main mismatch |
|---|---|---|---|
| HR / Super Admin | dashboard, applications, BUs, BU needs | recruitment manager; all BU data; user management differs | Not functionally identical: HR cannot see/assign Super Admin in `accounts/views.py` and serializers |
| BU Manager | dashboard, BUs, BU needs | own managed BU/memberships/needs only | Backend filtering is sound for URL-ID changes; BU frontend broken/incomplete |
| Candidate | dashboard, My Applications | own applications/documents/interviews; cancel/add document | No candidate application-detail route; candidate page embeds data instead |
| Intern | generic dashboard only | no domain endpoints | Role exists without module |
| Trainer | generic dashboard only (`TRAINER_TUTOR`) | no domain endpoints | Requested “Trainer” maps only to combined enum |
| Collaborator | generic dashboard only (`EMPLOYEE`) | may read own active BU and BU needs; membership endpoint denied | Sidebar hides BU data that backend permits |
| External Client | generic dashboard only (`CLIENT`) | no domain endpoints | Role exists without module |

Backend security observations:

- Candidate application/document querysets filter by `candidate_profile.user`; manually changing IDs returns 404 and document download rechecks ownership.
- BU manager querysets filter by `business_unit.manager`; manually changing IDs returns 404 before object mutation. Serializer validation also rejects another BU on create/update.
- Candidates/clients cannot access BU APIs. Collaborators receive read-only data only for active memberships.
- A collaborator’s backend BU read access is not represented in Angular navigation/routes—a frontend/backend mismatch, not a backend data leak.
- HR/Super Admin actions are enforced in Django recruitment action permissions, not merely Angular guards.
- `BusinessUnitViewSet` allows BU Managers to PATCH their BU including the `manager` field. Because the serializer does not validate manager role or prevent reassignment, a manager could attempt to transfer management. Model `clean()` is not automatically called by `save()`. This is a high-risk authorization/integrity gap.
- BU membership serializer does not restrict member roles; candidates/clients could be added and then remain blocked by role checks, creating inconsistent internal data.

## 7. Recruitment Workflow Audit

| Step | Status | Evidence / issue |
|---|---|---|
| 1 Candidate registration | Verified in source | Public serializer transaction creates candidate user/profile/application; `recruitment/serializers.py` |
| 2 Candidate login | Verified in source/frontend tests | JWT service and login component |
| 3 Candidate profile | Partial | Created and displayed; no dedicated edit API/page |
| 4 Offer listing | Missing | No Offer model/API/UI |
| 5 Offer details | Missing | No implementation |
| 6 Application submission | Verified in source/frontend tests | Multipart public form ↔ `public_submit` |
| 7 Internship type | Partial | Application types PFA/PFE/HIRING; not offer-driven |
| 8 CV upload | Verified in source | Required and validated |
| 9 Cover letter upload | Verified in source | Required and validated |
| 10 Additional document | Partial | Backend action/serializer exists; no Angular upload workflow after submission |
| 11 Candidate My Applications | Verified in source/frontend tests | Paginated page and candidate dashboard |
| 12 Candidate application details | Partial | Data shown in cards/dashboard; HR-only `applications/:id` route |
| 13 HR application list | Verified in source/frontend tests | Filters, pagination, states |
| 14 Super Admin application list | Verified in source | Same Angular/backend recruitment access |
| 15 Status changes | Substantial | State actions/services exist; full backend execution not run |
| 16 Document preview | Partial | Browser Blob URL open; depends on browser-supported file type |
| 17 Document download | Partial | Secure stream endpoint; UI primarily opens, not a clearly distinct download control |
| 18 Candidate notifications | Missing | Email helpers exist for workflow events, but no notification inbox/preferences/delivery tracking |
| 19 Django Admin display | Partial | Recruitment models registered; admin usability exists but backend checks not executed |

Upload security: size, extension, declared MIME, and magic prefix are checked in `recruitment/validators.py`. Access is protected through filtered querysets and explicit ownership checks. Gaps: MIME is client-supplied, DOCX only checks `PK`, there is no antivirus/content-disarm scan, filenames are retained for response headers, and no public endpoint throttling is configured.

## 8. Business Unit Audit

Backend:

- Models and initial migration exist for `BusinessUnit`, `BusinessUnitMembership`, and `BusinessUnitNeed`.
- DB uniqueness exists for BU name/code and membership `(business_unit,user)`; the latter prevents even a historical inactive duplicate, which may conflict with rejoining requirements.
- `BusinessUnit.clean()` checks manager role, but ordinary `objects.create()`/serializer saves do not invoke `full_clean()`. Serializer does not repeat that check.
- No validation ensures positive profile count beyond `PositiveIntegerField` semantics, expected date rules, status transitions, eligible membership roles, or one-manager/one-BU business rules.
- Queryset scoping protects manager cross-BU reads/writes. However, BU Manager PATCH can alter `manager`, and `BusinessUnitViewSet` has no `perform_update`/serializer authorization guard for that field.
- Admin registration and migration exist. Backend tests cover selected visibility/CRUD cases, but no tests cover manager reassignment, collaborator need access, candidate membership pollution, inactive membership behavior, or all mutations.

Frontend component classification:

| Component | Classification | Evidence |
|---|---|---|
| `bu-list` | Partially implemented | Real table/filter/pagination; broken service URL; missing create route; empty SCSS |
| `bu-needs-list` | Partially implemented | Real table/filter/pagination; broken URL; no create action; empty SCSS |
| `bu-detail` | Empty generated placeholder | `bu-detail works!` only |
| `bu-members` | Empty generated placeholder | `bu-members works!` only |
| `bu-need-detail` | Empty generated placeholder | `bu-need-detail works!` only |

All five are routed; none is unused. Sidebar exposes two list routes to HR/Super Admin/BU Manager. There are no BU Angular tests.

## 9. Authenticated UI Audit

- Layout: Material sidenav/toolbar with role-conditioned links, active states, user name, logout, and 900px breakpoint.
- Mobile: drawer switches to overlay and starts closed; menu button is labeled. Navigation does not automatically close after selection, and no handset-specific testing/spec exists.
- Dashboard: candidate role loads actual application data. Every other role receives the same generic identity card; there are no real KPIs. Thus dashboards are placeholders, although no fake numeric KPIs were found.
- Navigation definitions are split between route metadata, `ROLE_DASHBOARD_PATHS`, and layout condition methods; this creates duplication/drift risk.
- Collaborators can read BU data in Django but see no BU links and cannot enter BU routes due to Angular role metadata.
- BU list link `/business-units/new` is broken/misrouted. Placeholder routes are visible/reachable.
- BU templates contain extensive inline styles and empty component SCSS, inconsistent with the rest of the SCSS architecture.
- Encoding corruption is visibly user-facing in many labels.
- Accessibility positives: primary nav, menu, and paginators have labels; images generally have alt text. Gaps include text-only navigation without Material icons, limited focus/contrast evidence, no automated accessibility tests, and link/button purpose ambiguity for document preview/download.
- Responsive risks: data tables have wrappers but BU SCSS is empty, filter controls use inline flex rules, and no verified horizontal-overflow handling exists for small screens.

## 10. Errors and Risks

| ID | Severity | File path | Problem | Impact | Recommended correction |
|---|---|---|---|---|---|
| AUD-001 | Critical | repository Git state | Core application directories are untracked | Clone/deploy loses almost all product work | Review, stage intentionally, and commit cohesive changes after audit fixes |
| AUD-002 | High | `frontend/src/environments/environment.ts` | Production API points to localhost over HTTP | Deployed frontend cannot reach backend | Use deployment-time production API URL/HTTPS |
| AUD-003 | High | `frontend/src/app/core/services/business-unit.service.ts` | Extra slash in every BU endpoint | BU API integration fails or relies on redirect behavior | Normalize base URL construction and test requests |
| AUD-004 | High | `backend/apps/business_units/serializers.py`, `views.py` | BU Manager can submit manager reassignment; model `clean()` is not enforced | Privilege/data ownership integrity loss | Make manager immutable for BU Managers; validate role server-side; add adversarial tests |
| AUD-005 | High | `backend/apps/accounts/views.py`, `serializers.py`, `permissions.py` | HR/Super Admin equivalence is contradictory | Business decision not enforced consistently | Define one shared policy and update queries/serializers/tests |
| AUD-006 | High | `backend/config/settings/base.py` | Fallback secret and fallback DB credentials exist in base settings | Misconfigured deployment can start insecurely or target wrong DB | Require secrets/database in production and fail closed |
| AUD-007 | High | `backend/config/settings/base.py` | No REST throttling on public application/token endpoints | Spam, account/resource abuse, brute force | Add scoped throttles and gateway rate limits |
| AUD-008 | High | `backend/apps/recruitment/validators.py` | Upload validation lacks malware/content scanning | Malicious Office/PDF files can be stored/served | Scan/quarantine uploads and serve from private object storage |
| AUD-009 | Medium | `frontend/src/app/features/business-units/*` | Three routed placeholders and missing creation route | Visible unfinished product paths | Implement after fixing backend policies; hide only if explicitly approved |
| AUD-010 | Medium | `frontend/src/app/core/services/token-storage.service.ts`, interceptor | Refresh token stored in browser storage; no rotation/blacklist | XSS/session replay has larger blast radius | Threat-model storage; enable rotation/blacklisting or secure cookie architecture |
| AUD-011 | Medium | `backend/apps/business_units/models.py` | Membership uniqueness prevents historical rejoin rows | History semantics and reactivation workflows conflict | Decide history model; use conditional active uniqueness if required |
| AUD-012 | Medium | `frontend/src/app/app.routes.ts` | Collaborator backend access and frontend routes disagree | Legitimate data is inaccessible in UI | Align route/sidebar policy to approved requirements |
| AUD-013 | Medium | numerous new `.py/.ts/.html` files | Mojibake/encoding corruption | Broken French UI/admin text and maintainability | Standardize UTF-8 and correct affected literals |
| AUD-014 | Medium | `backend/config/settings/production.py` | Missing explicit redirect/referrer/frame/media/storage/email production configuration | Deployment security and file privacy incomplete | Add environment-specific hardening and private media strategy |
| AUD-015 | Medium | `frontend/package.json` | No lint/static-analysis script | Quality regressions are not gated | Configure Angular ESLint/format/type checks |
| AUD-016 | Medium | root infrastructure | Docker/Render/Vercel/GitHub workflows absent | Planned deployment is not reproducible | Add deployment only after application/security stabilization |
| AUD-017 | Low | `frontend/src/app/features/business-units/*.html` | Inline styling and empty SCSS | Inconsistent/responsive UI | Move styles into tested responsive SCSS |
| AUD-018 | Low | `backend/apps/business_units/tests.py` | Broad `assertRaises(Exception)` | Test can pass for wrong failure reason | Assert `IntegrityError` and transaction behavior precisely |

## 11. Test Audit

Existing backend suites:

- `backend/apps/accounts/tests.py`: model creation, JWT claims, `/me`, basic user permission cases.
- `backend/apps/recruitment/tests.py`: substantial workflow, permission, upload, retention, and document scenarios (source inspected, not executed).
- `backend/apps/business_units/tests.py`: model/queryset/role CRUD scenarios (source inspected, not executed).

Existing frontend suites: guards, auth/application services, dashboard, public form, candidate list, HR list, and application detail. Actual run: **31/31 passed** in Chrome 147. Build passed. No lint script exists, so lint was not run.

Backend execution results:

- First invocation: `python` was unavailable on PATH.
- Explicit bundled Python 3.12.13 invocation: all four required management commands failed before Django startup with `ModuleNotFoundError: No module named 'django'`.
- Therefore `check`, migration drift, migration state, and backend tests are **not verified**, and no pass/fail claim is made about them.

Missing/weak coverage:

- no BU frontend specs or service tests;
- no layout/sidebar/role-navigation specs;
- no end-to-end frontend-backend tests;
- no offers/notifications/training/etc. tests because modules do not exist;
- insufficient HR=Super Admin equivalence tests;
- missing manager reassignment and comprehensive cross-BU mutation tests;
- no XSS/accessibility/responsive/security-header/throttle/malware tests;
- no production-settings/deployment smoke tests;
- no test coverage report configured/executed.

No skipped/disabled tests were found by source search. No tracked tests were deleted in the current diff. Passing frontend tests cover only their 31 scenarios and do not validate BU connectivity or backend behavior.

## 12. Security and Configuration Audit

- Secrets: `.env.example` uses placeholders, but `base.py` contains an unsafe fallback secret and placeholder database URL. `production.py` forces the secret to exist, which is good if that module is actually selected.
- DEBUG/hosts/CORS: base is environment driven; local defaults DEBUG true. Production forces DEBUG false. CORS is allow-listed. There is no evidence of wildcard origins.
- HTTPS: production config has secure session/CSRF cookies, HSTS, proxy SSL header, and MIME sniff protection. It lacks `SECURE_SSL_REDIRECT`, explicit referrer policy, deployment host examples, and verified proxy configuration.
- JWT: 15-minute access and 7-day refresh defaults; no rotation, blacklist app, audience/issuer, or refresh revocation endpoint. Logout is client-side token deletion only.
- CSRF: JWT bearer API reduces normal CSRF exposure; Django admin/session remains protected by middleware.
- Files/media: authorization-protected API streaming is good. Direct `MEDIA_URL` serving is not wired in `urls.py`, but production storage/private-media design is absent. Never expose media through a public bucket URL without equivalent authorization.
- PostgreSQL: one Django DB configured; no network/container exposure config exists. Moodle is absent, so separate-database policy is not violated but is not implemented.
- URLs: both Angular environments hardcode `http://127.0.0.1:8000/api/`; production is invalid.
- Credentials/passwords: Django uses password hashing and validation. No plaintext password storage or Moodle password copy was found. Public registration accepts a password over the API, requiring HTTPS in deployment.
- Moodle, SSO, AI: none implemented, consistent with current “do not implement” direction except Moodle remains planned.
- Email: local console backend only; production delivery configuration is missing.

## 13. Progress Calculation

Scoring counts working connected behavior, not file presence.

| Category | Weight | Score | Weighted contribution | Basis |
|---|---:|---:|---:|---|
| Backend implementation | 25% | 32% | 8.00% | Auth, recruitment, and BU foundations exist; most product modules absent; backend runtime unverified |
| Frontend implementation | 25% | 30% | 7.50% | Public/auth/recruitment substantial; BU mostly incomplete; other role experiences placeholders |
| Frontend-backend integration | 20% | 35% | 7.00% | Auth/recruitment mapped; BU broken; most modules missing |
| Roles and security | 10% | 42% | 4.20% | Useful backend ownership filters; HR/Admin conflict, token/upload/throttle gaps |
| Tests and validation | 10% | 24% | 2.40% | 31 frontend tests pass; backend cannot run; major coverage gaps |
| Deployment and documentation | 10% | 10% | 1.00% | Basic docs/env example only; no deployment artifacts/CI |
| **Total** | **100%** |  | **30.10%** | Weighted sum |

This score is intentionally below a vertical-slice demo estimate because the target is the final multi-module application, not an MVP.

## 14. Prioritized Remaining Work

### Priority 1 — Blocking errors

- Put current untracked work under intentional version control after review.
- Provision backend dependencies and run all Django checks/tests/migration validation.
- Fix BU URL construction and missing/misrouted links.
- Close BU manager reassignment and HR/Super Admin policy gaps.
- Replace production localhost API configuration and resolve encoding corruption.

### Priority 2 — Core missing functionality

- Complete offers and offer-linked application workflow.
- Complete BU details, membership, and need forms/workflows.
- Define and implement intern/project/training/session/enrollment/attendance/evaluation/certificate modules.
- Add candidate profile/detail and notification functionality.
- Build real role dashboards and approved collaborator BU experience.

### Priority 3 — UI and quality improvements

- Consolidate navigation policy, add responsive/table/accessibility verification, and remove inline BU styling.
- Add lint/static analysis and comprehensive service/component/security tests.
- Improve error mapping, upload safety, session behavior, and observable loading states across modules.

### Priority 4 — Deployment and future integrations

- Add private media/object storage, production email, Docker, Render, Vercel, and GitHub CI/CD.
- Design Moodle integration later with separate databases, separate credentials, and no password copying. Do not add SSO or AI.

## 15. Recommended Next Sprint

1. **Objective:** establish a trustworthy baseline. **Affected:** Git working tree, dependency manifests. **Dependencies:** team review of untracked work. **Acceptance:** cohesive files committed; clean status; reproducible setup. **Tests:** clean-clone setup/build/check.
2. **Objective:** restore backend verification. **Affected:** `backend/requirements/*`, setup docs. **Dependencies:** PostgreSQL test credentials and Python environment. **Acceptance:** all four required management commands finish and results are recorded. **Tests:** full Django suite, migration drift/conflict checks.
3. **Objective:** secure BU ownership. **Affected:** BU serializers/views/models. **Dependencies:** final policy on manager assignment. **Acceptance:** BU Manager cannot read, mutate, or reassign another/own BU outside allowed fields; HR/Admin behavior identical where required. **Tests:** adversarial ID and PATCH tests.
4. **Objective:** repair BU connectivity. **Affected:** `business-unit.service.ts`, routes, list links. **Dependencies:** stable backend contract. **Acceptance:** lists reach correct URLs; no double slash; every visible link resolves. **Tests:** HttpTestingController service tests and router tests.
5. **Objective:** complete the existing BU slice (not add a new module). **Affected:** BU detail/members/need-detail and forms. **Dependencies:** tasks 3–4. **Acceptance:** placeholders removed; authorized CRUD, loading/error/empty states work. **Tests:** component and API permission tests.
6. **Objective:** make HR and Super Admin one functional role. **Affected:** accounts permissions/querysets/serializers, Angular role policy. **Dependencies:** migration/data decision about existing role labels. **Acceptance:** documented matrix and identical functional access while retaining labels if desired. **Tests:** paired role contract tests for every endpoint/action.
7. **Objective:** harden recruitment entry and files. **Affected:** DRF throttling, upload validation/storage, production settings. **Dependencies:** chosen scanner/private storage. **Acceptance:** rate limits, quarantine/scan, authorized delivery, safe failures. **Tests:** throttle, malicious-file, cross-user, and size/content tests.
8. **Objective:** correct production configuration. **Affected:** Angular environments/build config, Django production settings, `.env.example`. **Dependencies:** deployment URLs. **Acceptance:** no localhost/fallback secret in production; HTTPS/CORS/hosts/email/media explicitly configured. **Tests:** production configuration smoke check.
9. **Objective:** fix encoding and quality gates. **Affected:** new Python/Angular/templates, `package.json`, CI-ready scripts. **Dependencies:** none. **Acceptance:** UTF-8 French text renders correctly; lint/type/style commands configured. **Tests:** build, lint, frontend tests, backend formatting/static checks.
10. **Objective:** specify the next domain slice before implementation. **Affected:** architecture/API documentation for offers → applications → interns. **Dependencies:** stabilized auth/BU/recruitment contracts. **Acceptance:** approved models, permissions, role flows, API shapes, migrations, and test plan; explicitly excludes Moodle, SSO, and AI. **Tests:** reviewable acceptance scenarios and threat cases.
