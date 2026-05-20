# Frontend Implementation Checklist

Use this checklist when implementing or reviewing any page in the Personal Health Platform.

## 1. Page States

- [ ] Show a page-level loading state before data arrives.
- [ ] Show a clear empty state when data is missing.
- [ ] Show a success or completion state after async actions.
- [ ] Show an error state when an action fails.
- [ ] Do not leave the user with a silent blank page.

## 2. Shared Components

- [ ] Use `FlowBanner` for transient workflow feedback.
- [ ] Use `StateCard` for page-level or section-level loading and empty states.
- [ ] Use `DocumentFlowStepper` for upload / parse / confirm flows.
- [ ] Use the same tone and copy rules across all pages.

## 3. Dashboard

- [ ] First viewport shows health narrative, decision layer, and urgent items.
- [ ] Loading state appears before dashboard data is ready.
- [ ] Empty sections tell the user what to do next.
- [ ] Alerts, insights, and actions are clearly separated.

## 4. Documents

- [ ] Upload state is visible while files are being sent.
- [ ] Parse state is visible while OCR or extraction is running.
- [ ] Confirmation state is visible before data is written.
- [ ] Empty library state links back to upload.

## 5. Insights

- [ ] Initial loading is visible before insights arrive.
- [ ] Generate action shows success or failure feedback.
- [ ] Empty insights state explains how to create the first insight.
- [ ] Each insight has a clear why-now explanation.

## 6. Notifications

- [ ] Page explains that it is a prioritized queue, not a generic inbox.
- [ ] Loading state appears while alerts and insights are being ranked.
- [ ] Urgent, attention, and low-priority groups are visually separated.
- [ ] Snoozed items are not mixed into the active queue.

## 7. Actions

- [ ] Empty action lists show a next-step CTA.
- [ ] Overdue and improved actions are visually distinct.
- [ ] Feedback states explain whether the user is improving, stable, or worsening.

## 8. Timeline

- [ ] Narrative summary appears before the event stream when available.
- [ ] Empty timeline state explains what data is still missing.
- [ ] Timeline items remain readable by non-technical users.

## 9. Accessibility

- [ ] Every state is readable without relying on color only.
- [ ] Buttons and links remain keyboard accessible.
- [ ] Loading animations are optional and do not block understanding.

## 10. Final Review

- [ ] The user knows what is happening now.
- [ ] The user knows what to do next.
- [ ] The page uses the shared feedback language.
- [ ] The page avoids duplicate or conflicting state patterns.

