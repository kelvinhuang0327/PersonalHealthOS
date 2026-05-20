# Personal Health Platform Requirements and UI/UX Redesign Spec

## 0. Assumptions

- The primary user is a consumer managing personal health, not a clinician.
- The platform is a health analysis and follow-up product, not a diagnostic system.
- AI outputs must always be grounded in user data, show evidence, and include a medical disclaimer.
- The product should work as a modern web SaaS product with mobile-first interaction patterns and strong desktop usability.
- The current codebase already includes `dashboard`, `documents`, `timeline`, `profile`, `ai-summary`, `health-alerts`, and related backend services, so this spec assumes additive redesign rather than a ground-up rewrite.

## 1. Overall Requirement Analysis

The product should not be positioned as a passive health record repository. The real job to be done is:

1. help users understand what changed in their health,
2. surface what requires attention now,
3. reduce the effort to turn scattered health data into actions,
4. preserve trust by showing why the system says something.

That means the platform needs four layers working together:

1. data intake: profile, metrics, symptoms, documents, external devices,
2. interpretation: parsing, trend analysis, risk scoring, summary generation,
3. actioning: reminders, follow-up tasks, review queues, revisit prompts,
4. explainability: evidence, confidence, source trace, historical context.

The current product structure is functionally rich but experience-fragmented. In the current frontend:

- [Layout.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/components/Layout.tsx) exposes too many top-level destinations, making core jobs hard to find.
- [dashboard.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/dashboard.tsx) acts as a data dump instead of a daily command center.
- [documents.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/documents.tsx) and [documents-confirmation.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/documents-confirmation.tsx) are workflow-capable but still engineering-oriented.
- [timeline.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/timeline.tsx) and [profile.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/profile.tsx) expose raw structures rather than a productized experience.

The redesigned product should consolidate around five top-level jobs:

1. `Home`
2. `Reports`
3. `History`
4. `Actions`
5. `Profile`

System surfaces that should exist globally rather than as separate main pages:

- notification center,
- family member switcher,
- global upload entry,
- explainability drawer,
- search and filters.

## 2. Product Goal Summary

The platform should become a personal health operating system for one person, with optional family expansion later. Its core promise is:

"Bring all my health data together, tell me what matters, tell me why it matters, and tell me what I should do next."

Success means the user can do the following without friction:

- see their current health status within 10 seconds,
- understand which abnormalities are new, persistent, or worsening,
- upload a health report and safely turn it into usable structured data,
- review personal history with trends and explainable insights,
- keep their health context up to date without filling a giant settings form,
- trust that AI suggestions are evidence-based and non-diagnostic.

## 3. Core Module Analysis

### 3.1 Personal Health Summary and Notifications

#### Primary Goal

This page is the user's daily command center. It must answer three questions immediately:

1. am I okay right now,
2. what changed since last time,
3. what should I do next.

#### What the user actually needs

- a fast read of current status,
- a short list of important changes,
- clear next actions instead of generic advice,
- confidence that the system is not exaggerating risk,
- a reason to return daily through freshness and progress.

#### Required content

- today and this week summary,
- current overall health score and sub-scores,
- active risk alerts,
- newly abnormal or worsening indicators,
- pending follow-up tasks,
- reminders due soon,
- AI key insights,
- quick trend snapshots for core metrics,
- last updated timestamp,
- explainability entry point,
- medical disclaimer.

#### Recommended information hierarchy

1. Status hero
2. Critical alerts and urgent follow-ups
3. Top 3 actions for today
4. Health score and sub-score tiles
5. "Since your last visit" insight strip
6. Trend snapshot cards
7. Notification and task inbox preview
8. Deep links to reports, history, and profile

#### First-screen rule

The first screen should not start with charts. It should start with:

- current state,
- important change,
- next action.

If the first viewport shows multiple competing charts, the page has already failed.

#### How to avoid information overload

- show only the top three actionable items by default,
- group low-priority notifications into collapsible batches,
- separate urgent alerts from informative insights,
- use progressive disclosure for deeper evidence and raw values,
- keep chart previews miniature on `Home` and move detailed trend exploration to `History`.

#### How to drive daily return behavior

- show "since last visit" changes,
- keep reminders and follow-up tasks fresh,
- reinforce completed actions and streaks,
- surface one useful insight instead of five vague ones,
- provide a small sense of progress even when no risk exists.

#### Page-level IA

- Header: greeting, selected person, last sync time, global upload
- Hero band: overall status, score, primary message
- Alert rail: critical, high, medium
- Action queue: due today, overdue, recommended
- Insight cards: new abnormality, improvement, persistent issue
- Snapshot row: blood pressure, weight, glucose, sleep
- Notifications preview: upcoming checkup, follow-up, habit reminders
- Explainability drawer trigger

#### Core components

- `HealthStatusHero`
- `PriorityAlertRail`
- `TodayActionsPanel`
- `ScoreBreakdownCards`
- `SinceLastVisitCard`
- `MetricSnapshotSparkCards`
- `InsightDigest`
- `NotificationInboxPreview`
- `ExplainabilityDrawer`

#### AI role

- generate the short summary,
- prioritize what changed,
- translate abnormalities into plain language,
- propose next follow-up items,
- suppress low-value noise,
- attach evidence and confidence for each generated insight.

#### MVP vs advanced

MVP:

- overall summary,
- active alerts,
- health score,
- due reminders,
- top three actions,
- short AI insight digest.

Advanced:

- adaptive daily brief,
- personalized nudge timing,
- adherence prediction,
- "what improved your score" attribution.

### 3.2 Health Report Upload, Parsing, and Analysis

#### Primary Goal

Turn PDFs and images into trustworthy, confirmable, reusable health data.

#### What the user actually needs

- easy upload,
- quick parse feedback,
- confidence that the system did not misread the report,
- an efficient confirmation flow,
- direct connection from parsed report to long-term health understanding.

#### Required functions

- PDF and image upload,
- auto document type detection with manual override,
- OCR and text extraction,
- structured field extraction,
- reference range detection,
- abnormal flagging,
- parse confidence and uncertainty tagging,
- user confirmation before final write,
- historical report library,
- report summary,
- comparison against previous reports,
- follow-up suggestions.

#### Upload flow

1. Select or drag file
2. Auto-detect document type and date
3. Show processing state
4. Present extraction review screen
5. Require user confirmation for uncertain or abnormal items
6. Save confirmed values into structured records
7. Push results into timeline, alerts, score, and summary

#### Confirmation screen requirements

- original document preview,
- extracted report metadata,
- extracted item table,
- item-level editable fields,
- unit,
- reference range,
- abnormal flag,
- source snippet or page reference,
- confidence label,
- unresolved items queue,
- save and continue button,
- disclaimer that AI extraction may be imperfect.

#### Guardrails against misleading AI parsing

- never auto-write low-confidence values without confirmation,
- always show source evidence next to extracted result,
- visually separate confirmed vs suggested values,
- label inferred reference ranges differently from report-native ranges,
- require manual review for missing units or ambiguous analytes,
- do not generate medical diagnosis from parsed report alone.

#### Integration with overall health analysis

Confirmed report data should become first-class longitudinal data. After confirmation, the system should:

- create lab report records,
- append lab items to timeline,
- update abnormal indicators,
- trigger risk rules,
- refresh health score,
- enrich AI summary,
- create follow-up tasks when needed.

#### Page-level IA

- Stepper header: upload, parse, review, confirm, insights
- Left pane: document preview and metadata
- Right pane: extraction table and issues
- Top summary: parse result, abnormal count, confidence status
- Review tabs: abnormal first, all values, unresolved, previous comparison
- Footer actions: save draft, confirm, re-upload
- Post-confirm state: analysis summary and next actions

#### Core components

- `DocumentDropzone`
- `ParseProgressCard`
- `ReportMetadataPanel`
- `ExtractedValuesTable`
- `ConfidenceBadge`
- `SourceEvidencePopover`
- `AbnormalSummaryBanner`
- `CompareWithPreviousPanel`
- `ReviewQueueTabs`
- `ConfirmAndWriteBar`

#### AI role

- field extraction candidate generation,
- item normalization,
- inferred reference range suggestion,
- report-level summary,
- abnormality explanation in plain language,
- recommended follow-up list.

#### MVP vs advanced

MVP:

- upload,
- parse,
- abnormal flagging,
- confirmation,
- summary,
- longitudinal save.

Advanced:

- multi-page side-by-side diff,
- per-lab institution reference management,
- auto grouping by panel type,
- clinician-ready structured export.

### 3.3 Personal History Overview and Analysis

#### Primary Goal

Help the user understand patterns over time, not just see isolated records.

#### What the user actually needs

- a sense of progression,
- clear turning points,
- visibility into relationships between symptoms, labs, and metrics,
- distinction between one-off anomalies and persistent trends,
- explanations that reference data rather than magic conclusions.

#### Recommended page model

This page should be a hybrid of summary plus timeline, not only one or the other.

- summary is needed for fast orientation,
- timeline is needed for narrative and event order,
- charts are needed for continuous measures,
- explainability is needed to build trust.

#### Best data presentation by type

Use charts for:

- blood pressure,
- weight,
- glucose,
- sleep,
- health score,
- repeated lab indicators.

Use event stream or timeline for:

- symptom onsets,
- uploaded reports,
- AI insights,
- alerts,
- medication or follow-up events,
- notable lifestyle changes.

Use comparison tables for:

- before vs after periods,
- panel-to-panel lab comparisons,
- symptom frequency change,
- task completion impact.

#### Historical AI analysis responsibilities

AI should identify:

- patterns,
- worsening sequences,
- recovery trends,
- repeated abnormalities,
- possible trigger windows,
- behavior changes that correlate with improvements.

But every conclusion must include:

- time window,
- evidence items,
- confidence,
- limitations,
- alternative explanation when relevant.

#### Explainability model

Every major insight should support a "Why am I seeing this?" drill-down:

- source metrics,
- source symptoms,
- source reports,
- change window,
- confidence level,
- whether the conclusion is rule-based, trend-based, or AI-generated.

#### Page-level IA

- Header: timeframe, filters, comparison mode
- Overview band: score trend, major changes, risk movement
- Chart zone: trends for selected metrics
- Insight rail: worsening, improving, persistent
- Mixed timeline: symptoms, reports, metrics, alerts
- Comparison drawer: period A vs period B
- Explainability panel: evidence and reasoning

#### Core components

- `TimeRangeSwitcher`
- `HistoryOverviewBand`
- `TrendChartGrid`
- `ChangePointCards`
- `MixedEventTimeline`
- `PatternInsightCards`
- `ComparePeriodsDrawer`
- `ExplainabilityPanel`

#### MVP vs advanced

MVP:

- mixed timeline,
- trend charts,
- AI pattern summaries,
- important change points,
- period filters.

Advanced:

- correlation explorer,
- intervention impact analysis,
- custom cohorts and benchmarks,
- wearable event overlays.

### 3.4 Profile Management

#### Primary Goal

Build and maintain health context without making the page feel like a back-office settings screen.

#### What the user actually needs

- a simple place to keep core health context current,
- visibility into what data affects AI interpretation,
- lightweight control over notifications and privacy,
- optional family/dependent context without complexity overload.

#### Fields that should be collected in MVP

- name or display name,
- date of birth or age,
- sex at birth where medically relevant,
- height,
- weight,
- allergies,
- chronic conditions,
- family history,
- baseline medications,
- notification preferences,
- consent and privacy controls.

#### Fields that can be progressive later

- lifestyle habits,
- exercise frequency,
- sleep goals,
- diet preferences,
- care team information,
- insurance,
- emergency contact,
- device linkages,
- advanced sharing permissions.

#### Fields that directly affect AI analysis

- age,
- sex at birth if used for reference ranges,
- height and weight,
- chronic conditions,
- allergies,
- medications,
- family history,
- smoking or alcohol use if collected,
- pregnancy status if relevant,
- current health goals.

#### How to reduce fill burden

- ask only what changes interpretation or reminders,
- show profile completion with health impact messaging,
- use guided cards instead of long forms,
- allow report import to prefill fields,
- auto-suggest updates from parsed reports,
- separate required now from useful later.

#### Page-level IA

- Profile summary hero
- Health context sections
- AI relevance labels on fields
- Family member switcher and profiles
- Notification preferences
- Privacy and consent center
- Account and security

#### Core components

- `ProfileSummaryCard`
- `ProfileCompletenessCard`
- `HealthContextSection`
- `AIImpactBadge`
- `MedicationListEditor`
- `FamilyProfilesPanel`
- `NotificationPreferencesCard`
- `PrivacyConsentPanel`
- `AccountSecurityPanel`

#### UX principle

This page should feel like "my health context" rather than "system settings". The UI should explain why each section matters.

#### MVP vs advanced

MVP:

- core health context,
- notification preferences,
- account/security,
- privacy basics.

Advanced:

- family governance,
- delegated caregiver access,
- fine-grained sharing policies,
- device permissions dashboard.

## 4. Additional Important Modules

### Must add to MVP

#### Symptom Capture

Why it matters:

- symptoms often explain changes that metrics alone cannot.

What it should include:

- quick add,
- free-text description,
- severity,
- optional duration,
- optional body area,
- recurrence,
- AI normalization to symptom tags.

#### Action and Follow-Up Module

Why it matters:

- insight without action has low retention and low value.

What it should include:

- follow-up tasks,
- user tasks,
- recurring habits,
- due dates,
- snooze,
- done state,
- reason and evidence.

#### Explainability and Evidence Center

Why it matters:

- trust in healthcare products depends on explainability.

What it should include:

- evidence list,
- confidence,
- rule-based vs AI badge,
- source links to reports and metrics,
- "what data was used" view.

#### Notification Center

Why it matters:

- notifications need a proper inbox model, not just banners on the dashboard.

What it should include:

- unread state,
- priority,
- category,
- action,
- snooze,
- archive,
- preference mapping.

### Recommended for next phase

- wearable integration,
- family health management,
- medication adherence,
- clinical export and share,
- care plan templates,
- PDF health report generation,
- behavior analytics,
- benchmark comparisons,
- chat-style guided health review.

## 5. Data Relationships and Dependencies

### Core entity flow

- `User`
- `PersonProfile`
- `UserProfile`
- `HealthMetric`
- `SymptomLog`
- `MedicalDocument`
- `LabReport`
- `LabReportItem`
- `RiskAlert`
- `AISummary`
- `HealthScore`
- `Notification`
- `Task`

### Dependency model

- Profile data affects reference ranges, interpretation, reminders, and risk weighting.
- Document parsing produces lab reports and items.
- Confirmed lab items feed alerts, score, timeline, summary, and risk prediction.
- Metrics and symptoms feed trend analysis, timeline, pattern detection, and health score.
- Alerts and insights create or recommend tasks.
- Notifications are transport and delivery objects for alerts, reminders, tasks, and summaries.
- Explainability objects reference the exact evidence rows used by AI or rules.

### Derived objects that should exist even if not all are separate tables yet

- `Insight`
- `Task`
- `NotificationEvent`
- `EvidenceReference`
- `DataQualityIssue`

## 6. Suggested Information Architecture by Page

### Home

- current status,
- top actions,
- active alerts,
- summary insights,
- due reminders,
- small trend previews.

### Reports

- upload area,
- file library,
- parse queue,
- review and confirm workflow,
- report analysis summary,
- long-term report comparison.

### History

- mixed timeline,
- trends,
- period comparison,
- pattern insights,
- explainability.

### Actions

- follow-up tasks,
- reminders,
- routines,
- notification inbox,
- completed history.

### Profile

- health context,
- medical background,
- goals,
- family profiles,
- privacy,
- account and security.

## 7. Main Blocks and Components by Page

### Home

- `HomeHero`
- `UrgencyRail`
- `ActionQueue`
- `ScoreTiles`
- `InsightCards`
- `MiniTrendCards`
- `ReminderList`
- `ExplainabilityDrawer`

### Reports

- `UploadDropzone`
- `DocumentLibrary`
- `ParseStatusList`
- `ExtractionReviewTable`
- `DocumentPreviewPane`
- `AbnormalItemSummary`
- `ComparisonPanel`
- `PostConfirmInsightPanel`

### History

- `TimeFilterBar`
- `SummaryBand`
- `TrendChartTabs`
- `EventTimeline`
- `PatternCards`
- `CompareModeDrawer`
- `EvidenceDrawer`

### Actions

- `ActionInbox`
- `ReminderBuckets`
- `HabitCards`
- `FollowUpBoard`
- `CompletedLog`

### Profile

- `ProfileHero`
- `HealthContextCards`
- `ConditionEditors`
- `MedicationEditor`
- `GoalCards`
- `FamilySwitcher`
- `NotificationSettings`
- `PrivacyCenter`

## 8. AI Role by Module

### Summary and Notifications

- generate daily and weekly health digest,
- prioritize changes,
- convert data to plain-language insight,
- recommend actions,
- suppress low-value notifications.

### Report Parsing and Analysis

- extract fields,
- normalize analytes,
- infer likely ranges when missing,
- summarize abnormalities,
- propose tracking items.

### History and Analysis

- detect trend direction,
- flag persistent abnormalities,
- detect change points,
- cluster symptom patterns,
- generate evidence-based historical narratives.

### Profile

- explain why missing fields matter,
- suggest profile updates,
- infer likely relevant context from uploaded reports,
- tailor recommendations to health goals.

### Guardrails that apply everywhere

- no diagnosis claims,
- no medication or treatment instructions beyond general guidance,
- every major conclusion must cite evidence,
- surface uncertainty,
- require human confirmation for ambiguous extracted data.

## 9. Reminder, Notification, Insight, and Risk Design

### Reminder

- time-based or schedule-based,
- usually expected,
- actionable,
- snoozable,
- medium urgency by default.

Examples:

- repeat glucose check tomorrow,
- annual checkup due in 30 days,
- confirm parsed report.

### Notification

- delivery object or inbox item,
- can represent reminders, insights, alerts, or task updates,
- should have priority, status, source, and action.

### Insight

- interpretive and usually non-urgent,
- explains a pattern or change,
- should not hijack the urgent notification channel.

Examples:

- your average sleep improved over the last two weeks,
- fasting glucose has been mildly elevated across three reports.

### Risk Alert

- abnormal or elevated risk requiring attention,
- higher urgency,
- should include severity, reason, and recommended next step,
- can escalate channels if the user opts in.

Examples:

- confirmed blood pressure values remain in high range,
- liver function markers worsened compared with prior report.

### Task

- explicit action object with due date and completion state,
- may be user-created or system-created.

Examples:

- recheck blood pressure for three consecutive mornings,
- review abnormal report items,
- book follow-up screening.

### Priority model

- `Critical`: possible urgent issue, strong risk or repeated worsening
- `High`: needs follow-up soon
- `Medium`: useful but not time-sensitive
- `Low`: informational or motivational

## 10. MVP Necessary Feature List

- streamlined top-level IA with `Home`, `Reports`, `History`, `Actions`, `Profile`
- health summary home page
- notification center with priority and category
- follow-up task model
- upload, parse, review, and confirm report workflow
- abnormal flagging with source evidence
- structured longitudinal lab storage
- mixed timeline and trend view
- explainability drawer for AI outputs
- profile completion and AI-relevant health context
- reminder preferences
- health score and risk summary
- medical disclaimer and confidence labeling

## 11. Advanced Feature List

- wearable syncing,
- family health management and caregiver mode,
- advanced risk forecasting,
- medication tracking,
- intervention effectiveness analysis,
- custom cohort benchmarks,
- clinician share links,
- PDF health report export,
- AI chat copilot grounded in platform data,
- multi-source ingestion from hospital portals and labs.

## 12. Easily Missed but Important

- data provenance on every AI conclusion,
- explicit handling of uncertain parse results,
- unit normalization,
- age and sex-specific reference logic,
- notification fatigue controls,
- draft autosave in confirmation flows,
- timeline consistency across metrics, symptoms, and documents,
- empty states that teach the user what to do next,
- privacy and consent transparency,
- audit trail for edited parsed values.

## 13. Overdesign to Avoid Early

- chat-first UI for every interaction,
- disease diagnosis positioning,
- too many scores,
- real-time wearable dashboards before data quality is stable,
- excessive custom chart types,
- too many top-level pages,
- full caregiver/family permission graph before single-user experience is excellent,
- fully automated document write-through without confirmation,
- ML prediction claims without reliable longitudinal data volume.

## 14. How the `ui-ux-pro-max-skill` Was Applied

The repository at [ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) was applied as a design methodology, not as a literal style picker.

### Applied workflow

1. Generate a design-system baseline first, before discussing page visuals.
2. Use page-specific override files instead of reusing one visual recipe everywhere.
3. Use the skill's UX checklist as a hard quality gate for accessibility, interaction, navigation, loading feedback, and chart usage.
4. Keep top-level navigation within a small number of jobs.
5. Use progressive disclosure so health pages feel trustworthy instead of dense and noisy.

### Generated artifacts

- [MASTER.md](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/docs/ui-ux-skill/design-system/personal-health-platform/MASTER.md)
- [dashboard.md](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/docs/ui-ux-skill/design-system/personal-health-platform/pages/dashboard.md)
- [reports-workflow.md](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/docs/ui-ux-skill/design-system/personal-health-platform/pages/reports-workflow.md)
- [history-analysis.md](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/docs/ui-ux-skill/design-system/personal-health-platform/pages/history-analysis.md)
- [profile-management.md](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/docs/ui-ux-skill/design-system/personal-health-platform/pages/profile-management.md)
- [notifications-center.md](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/docs/ui-ux-skill/design-system/personal-health-platform/pages/notifications-center.md)

### How this skill was curated for healthcare

The repo's raw search output was not adopted blindly. Some auto-matched styles were rejected because they reduce healthcare trust or readability.

Rejected directions:

- dark-first history analysis,
- neumorphism for profile management,
- overly technical monitoring visuals for patient-facing summary pages.

Accepted methodology:

- master plus page-overrides structure,
- data-dense but scannable layout logic,
- action-first page hierarchy,
- accessibility and feedback checklist,
- chart and navigation selection rules.

## 15. Redesigned UI/UX Principles

- trustworthy before flashy,
- action-first before data-first,
- summary before detail,
- abnormal first, but not alarmist,
- evidence visible, not hidden,
- progressive disclosure for dense health content,
- readable typography and generous contrast,
- consistent risk color semantics,
- mixed view design: cards for priority, charts for trends, timelines for narrative,
- every important AI output needs a visible "why".

### Visual language

- light-first medical SaaS aesthetic,
- structured grid, calm cyan-blue base, green for positive, amber for caution, red only for meaningful risk,
- Figtree for headings, Noto Sans for body,
- restrained motion,
- card depth kept subtle,
- icon-led scanning with consistent icon set,
- no AI-themed purple gradients or gimmicky glassmorphism.

## 16. Improvements Over the Current Engineering-Led Pages

### Current issues

- Too many navigation endpoints in [Layout.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/components/Layout.tsx).
- The home experience in [dashboard.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/dashboard.tsx) lacks action hierarchy.
- The report confirmation experience in [documents-confirmation.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/documents-confirmation.tsx) relies on raw JSON editing.
- The history page in [timeline.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/timeline.tsx) is developer-readable, not user-readable.
- The profile page in [profile.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/profile.tsx) mixes user settings, health context, security, and family management without product structure.

### Redesign improvements

- consolidate many pages into fewer user jobs,
- replace raw JSON surfaces with guided review UI,
- convert generic alert lists into prioritized action flows,
- move deep detail into drawers and tabs,
- add confidence, evidence, and source trace to AI features,
- make charts and timelines complementary instead of competitive,
- separate summary, alerts, tasks, and insights into distinct roles.

## 17. Core Pages That Need Refactoring

### Highest priority

- [Layout.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/components/Layout.tsx)
- [dashboard.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/dashboard.tsx)
- [documents.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/documents.tsx)
- [documents-confirmation.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/documents-confirmation.tsx)
- [timeline.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/timeline.tsx)
- [profile.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/profile.tsx)

### Merge or demote from top-level nav

- [ai-summary.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/ai-summary.tsx)
- [health-alerts.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/health-alerts.tsx)
- [health-insights.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/health-insights.tsx)
- [health-analysis.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/health-analysis.tsx)
- [trends.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/trends.tsx)
- [records.tsx](/Users/kelvin/Kelvin-WorkSpace/PersonalHealthOS/frontend/pages/records.tsx)

These should become subviews inside the new `Home`, `Reports`, `History`, and `Actions` structure rather than remain separate major destinations.

## 18. Recommended Refactor Order for Frontend Engineers

1. Rebuild the global IA and navigation shell.
2. Rebuild `Home` because it defines the product's mental model.
3. Rebuild the report workflow because it is the highest-trust flow.
4. Rebuild `History` with shared chart and timeline primitives.
5. Rebuild `Actions` and notification center.
6. Rebuild `Profile` around health context and privacy.
7. Backfill secondary pages and retire redundant routes.

### Component-first build order

1. navigation shell and page container
2. status hero, priority rail, score tiles
3. task and reminder components
4. document upload and review table
5. trend chart cards and timeline items
6. evidence drawer and explainability primitives
7. profile context cards and settings panels

## 19. Execution Guidance

If this spec is used for design and implementation, the next practical outputs should be:

1. route map and sitemap,
2. wireframes for `Home`, `Reports`, `History`, `Actions`, `Profile`,
3. component inventory with props contracts,
4. data contract alignment between frontend and backend,
5. notification and task domain model,
6. evidence and confidence schema for AI outputs.

## 20. Shared UI Feedback Standards

The product now uses a shared feedback language for loading, success, empty, warning, and error states.

Reference:

- [UI_FEEDBACK_STANDARDS.md](/Users/kelvin/Kelvin-Workspace/PersonalHealthOS/docs/UI_FEEDBACK_STANDARDS.md)
- [FRONTEND_IMPLEMENTATION_CHECKLIST.md](/Users/kelvin/Kelvin-Workspace/PersonalHealthOS/docs/FRONTEND_IMPLEMENTATION_CHECKLIST.md)

Use this standard whenever a page or section needs to communicate:

1. what is happening now,
2. what changed after an action,
3. what the user should do next.

Shared building blocks:

- `FlowBanner` for transient workflow feedback,
- `StateCard` for page-level or section-level loading and empty states,
- `DocumentFlowStepper` for multi-step document workflows.
