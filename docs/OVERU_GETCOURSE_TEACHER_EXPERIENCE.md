# OverU — GetCourse-style teacher experience (Marina-first)

## Product decision
Preserve the Frappe Learning backend and real course/student data; redesign its workflows for a non-technical course creator. Do NOT replace production or re-create features already provided by Frappe.

### Primary teacher navigation
1. **Сегодня / Рабочий стол** — requires-review queue (ungraded assignments; new course questions; group notifications), clear counts and links.
2. **Мои курсы** — courses > chapters/modules > lessons; create lesson and preview student view.
3. **Ответы учеников** — unified submissions, quick filter “Требует проверки”, approve/return with feedback, attachment preview, full history.
4. **Обсуждения** — lesson-specific public/teacher-only threads; threaded replies; moderation; unread status.
5. **Группы и потоки** — batches, memberships, course access, announcements, optional batch discussions.
6. **Ученики** — single student page with enrollment, progress, submissions, feedback.
7. **Настройки** — advanced admin features only, not in primary teacher flow.

### Current repository audit (confirmed from source)
- Learning engine: Frappe Learning (README.md), not GetCourse.
- Existing course structure: frontend/src/pages/Courses/CourseEditor.vue, CourseDetail.vue; chapter and lesson doctypes.
- Assignment queue: frontend/src/pages/AssignmentSubmissions.vue and components/Submissions/SubmissionsPage.vue; statuses Pass/Fail/Not Graded; permissions Course Creator vs moderator.
- Discussions: frontend/src/components/Discussions.vue, DiscussionReplies.vue, Modals/DiscussionModal.vue; threads already exist.
- Groups: frontend/src/pages/Batches/*; LMS Batch and Batch Enrollment.
- Navigation: frontend/src/components/Sidebar/AppSidebar.vue and src/utils/sidebarRows; settings can customize sidebar.
- This feature branch starts with a discoverable **Student answers** header and **Needs review** toggle, using the existing URL/status filter.

### Workflows
**Teacher:** Home > needs review > select answer > read attachment > write feedback > accept or request revision > next answer. Return to same filtered queue and remember previous filters. Do not expose delete to Course Creator.

**Teacher creates lesson:** Courses > course > chapter > add lesson > choose video/text/file/quiz/assignment > publish or draft > preview as student. Drafts and attachments must stay private.

**Student:** My learning > course > module > lesson > content > question/comment or submit homework > see review status and teacher reply. Keep comments separate from homework; do not display classmates' private homework.

**Batch:** Course > link groups/batches with enrollment > show learner list and progress > private group discussion / announcements, with strictly scoped access.

### Feature requirements and API/security checks
- Reuse existing doctypes and routes where possible.
- Check current permissions server-side for all new read/write APIs. Course Creators see only their assigned courses/students; students only enrolled published content and own submissions.
- Distinguish discussion visibility: public to enrolled learners vs instructor-only. No insecure client-only filtering.
- Ensure private file storage, secure upload, MIME validation, XSS escaping, spam protections, rate limits, and careful email notification defaults.
- Staged rollout via feature flag for teacher roles; no breaking URL changes; preserve legacy navigation fallback.
- Ship no destructive migrations without verified encrypted backup and rollback.
- No dummy data in real teacher/student screens. All counts derived from actual records.

### Acceptance tests
1. Marina can create a course with two chapters, three lessons, a video, attachment and assignment without entering Desk.
2. Teacher review queue combines assignments from all authorized courses; Needs Review filters Not Graded and opening a submission works.
3. Student submits answer + file; teacher reviews, comments and requests revision; student sees outcome.
4. Lesson questions and replies are accessible to authorized users only; hidden questions stay hidden.
5. Two batches of the same course keep members, discussions and notifications separate.
6. Unpublished lesson and PDF cannot be opened by an anonymous user; student from wrong batch cannot access protected lessons/files.
7. Keyboard, mobile widths, screen reader labels, Russian text and long titles work.
8. No regression in existing course creation, tests, migrations or deployed services.

### Implementation map (complete product scope, staged merges)
- **A — Teacher shell:** dedicated layout and workspace home, simplify sidebar, place low-frequency tools behind Settings.
- **B — Course builder:** module tree, add/reorder lessons, simplified lesson editor with templates and student preview.
- **C — Discussions:** thread view in lessons, visibility controls, activity and moderation; notification counters.
- **D — Assignments:** review queue, inline feedback, bulk navigation (not bulk deletion), revision state and teacher/student history.
- **E — Batches:** group pages, members, announcements, group-scoped discussions, access verification.
- **F — Quality:** backend authorization, E2E tests, release flag, training walkthrough for Marina, staged rollout.

### Release gates
Do not deploy this branch to overu.online until code review, frontend typecheck/build, backend and E2E authorization tests, staging smoke test under Marina/learner/anonymous roles and rollback are ready. Production image and current course data must remain untouched during development.

### References (public interface and product behavior)
- https://getcourse.ru/blog/276118 (teacher answers)
- https://getcourse.ru/blog/1171225 (course structure)
- https://getcourse.ru/blog/1203081 (mobile)
- Frappe source and tests in this repository.

## Progress on this branch
- [x] Make the current assignment submission queue more prominent and add a needs-review shortcut.
- [ ] Teacher dashboard / aggregated counters
- [ ] Course editor UX
- [ ] Lesson discussion visibility
- [ ] Review feedback and revisions
- [ ] Batch-level community
- [ ] E2E tests / staged deployment
