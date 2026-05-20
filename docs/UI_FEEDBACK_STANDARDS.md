# UI Feedback Standards for Health Insights Platform

## Purpose

This document defines the shared feedback language for the Personal Health Platform UI so that all pages present loading, success, empty, warning, and error states in a consistent way.

The goal is to reduce uncertainty during asynchronous operations and to prevent each page from inventing its own state language.

## Core Principle

Every user-facing workflow should answer three questions:

1. What is happening now?
2. What should I do next?
3. What changed after my action?

If a state cannot answer at least one of these clearly, it should be redesigned.

## Shared Components

### `FlowBanner`

Use for transient workflow feedback:

- loading
- success
- info
- warning
- error

Best use cases:

- report upload in progress
- insight generation in progress
- profile save success/failure
- person switch confirmation
- parse or confirmation progress

### `StateCard`

Use for page-level or section-level states:

- initial loading
- empty state
- no-data state
- stable success state
- neutral informational state

Best use cases:

- dashboard initial loading
- empty action inbox
- empty notifications section
- empty timeline
- empty report library

### `DocumentFlowStepper`

Use only for multi-step document workflows where the user must understand which step they are on:

- upload
- parse
- confirm

## State Tone Mapping

### Loading

Use when the system is working and the user should wait.

Copy pattern:

- title: what is being processed
- message: what the system is doing
- optional hint: what will happen next

Examples:

- 正在整理你的健康摘要
- 正在上傳報告
- 正在產生洞察

### Success

Use when an action has completed and the user should understand the result.

Copy pattern:

- title: what finished
- message: what changed
- next step: what the user should do now

Examples:

- 文件上傳完成
- 洞察已更新
- 已切換檢視對象

### Empty

Use when data is missing or there are no items to show.

Copy pattern:

- title: what is missing
- message: why this matters
- action: the most useful next step

Examples:

- 還沒有報告
- 目前沒有任務
- 還沒有足夠資料形成洞察

### Warning

Use when the page is usable but the user should be aware of a risk or limitation.

Examples:

- high-priority reminder pending
- parse confidence is low
- data is outdated

### Error

Use when an action failed and needs retry or correction.

Examples:

- file upload failed
- insight generation failed
- profile save failed

## Page-Level Rules

### Dashboard

The first viewport should show:

- page-level loading state if data has not arrived yet
- health narrative
- decision layer / next actions
- priority alerts

Avoid:

- showing only charts first
- showing blank cards before data is loaded

### Documents

The user must always know:

- whether the file is being uploaded
- whether parsing has started
- whether confirmation is needed

Use:

- `DocumentFlowStepper`
- `FlowBanner`
- `StateCard` for empty library

### Insights

The page should distinguish:

- loading state
- generated insights
- empty state when there is no data yet

Do not leave the user with a silent blank area after clicking generate.

### Notifications

This page is not a general notification list.

It is a prioritized queue. When empty, use a clear neutral state that still explains the queue concept.

### Actions

When no task exists, show a state card that pushes the user toward the next best source:

- dashboard
- notifications center
- insights

### Timeline

When narrative history exists, show a dedicated narrative summary card above the event stream.

When no narrative exists, explain that enough data is needed before the story can be formed.

## Copy Guidelines

Keep messages:

- short
- specific
- action-oriented
- free from raw scores unless the user is already in an analytics context

Avoid:

- vague filler like "something went wrong"
- technical jargon
- mixed English and Chinese in the same user-facing state

## Accessibility Notes

- Loading states should still be readable without relying only on animation.
- Empty states should include a visible next step.
- Buttons in state cards should remain keyboard accessible.
- Do not use color alone to communicate tone.

## Implementation Guidance

Recommended component placement:

- `frontend/app/components/platform/flow-banner.tsx`
- `frontend/app/components/platform/state-card.tsx`
- `frontend/components/redesign/document-flow-stepper.tsx`

Recommended usage pattern:

1. show page loading state on first render
2. show section empty state when data is absent
3. show banner feedback for async action result
4. show next-step CTA in every empty or successful state

## Review Checklist

Before shipping a page:

- Does the user know what is happening?
- Does the user know what to do next?
- Does the page avoid blank or silent transitions?
- Does the page use the shared state language?
- Does the page avoid duplicate state components?

