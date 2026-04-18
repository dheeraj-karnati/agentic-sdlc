# Product Requirements Document — TaskFlow

## Overview

TaskFlow is a project management SaaS for small engineering teams (5-20 people).
Think "Linear meets Notion" — fast, keyboard-driven, opinionated about workflow.

## User Roles

- **Admin**: Full system access, billing, team management, workspace settings
- **Manager**: Create projects, assign tasks, view reports, manage sprints
- **Member**: Create/edit tasks, log time, comment, update status
- **Viewer**: Read-only access to projects and tasks (for stakeholders)

## Core Features

### 1. Projects
- Each workspace can have multiple projects
- Projects have: name, description, status (active/archived), color, icon
- Projects contain tasks organized into sprints or a backlog

### 2. Tasks
- Fields: title, description (rich text), status, priority, assignee, 
  due date, story points, labels, sprint
- Status workflow: Backlog → Todo → In Progress → In Review → Done
- Priority levels: Urgent, High, Medium, Low (color-coded)
- Tasks can have subtasks (one level deep)
- Tasks can block other tasks (dependency tracking)
- File attachments (up to 10MB each, stored in S3)
- Comment thread per task with @mentions

### 3. Sprints
- Fixed 2-week duration by default (configurable per project)
- Sprint planning: drag tasks from backlog into sprint
- Sprint board: Kanban view grouped by status
- Sprint burndown chart
- Sprint retrospective notes

### 4. Time Tracking
- Members can log time against tasks
- Automatic timer (start/stop) or manual entry
- Weekly timesheet view per member
- Manager can view team time allocation report

### 5. Search & Filters
- Global search across all projects and tasks
- Filter by: status, priority, assignee, label, sprint, date range
- Saved filters (custom views)
- Keyboard shortcut: Cmd+K to open search

### 6. Notifications
- In-app notifications for: assignment, mention, status change, comment, due date
- Email digest: daily summary of changes (configurable)
- Slack integration: post updates to a channel

### 7. Dashboard
- Personal dashboard: my tasks, overdue items, upcoming due dates
- Manager dashboard: team velocity, sprint progress, blockers
- Project dashboard: task distribution, completion rate

## Non-Functional Requirements

- Response time: < 200ms for page loads (p95)
- Support 500 concurrent users per workspace
- 99.9% uptime SLA
- SOC2 Type II compliance required
- Data encrypted at rest (AES-256) and in transit (TLS 1.3)
- GDPR compliant: data export, account deletion
- Mobile responsive (no native app required for v1)

## Integrations (v2, not in scope for v1)
- GitHub: link PRs to tasks
- Slack: bidirectional sync
- Google Calendar: sync due dates

## Constraints
- Budget: $200K for v1
- Timeline: MVP in 8 weeks
- Team: 2 backend, 1 frontend, 1 designer
- Stack preference: Next.js frontend, Python backend (FastAPI), PostgreSQL
