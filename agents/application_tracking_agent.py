from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Dict, Iterable, List, Optional


STATUS_ORDER = {
    "saved": 10,
    "generated": 20,
    "applied": 30,
    "interviewing": 40,
    "offer": 50,
    "rejected": 90,
    "withdrawn": 90,
}

TERMINAL_STATUSES = {"offer", "rejected", "withdrawn"}


@dataclass
class ApplicationTrackingInsight:
    application_id: str
    status: str
    deadline_status: str
    days_until_deadline: Optional[int]
    urgency: str
    next_action: str
    summary: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "application_id": self.application_id,
            "status": self.status,
            "deadline_status": self.deadline_status,
            "days_until_deadline": self.days_until_deadline,
            "urgency": self.urgency,
            "next_action": self.next_action,
            "summary": self.summary,
        }


class ApplicationTrackingAgent:
    """Deterministic application tracker for status, deadlines, and next actions."""

    def inspect_application(self, application: Any, job: Any = None) -> Dict[str, Any]:
        now = datetime.now(UTC).replace(tzinfo=None)
        status = (getattr(application, "status", None) or "saved").strip().lower()
        deadline = getattr(application, "deadline_at", None)
        days_until = self._days_until(deadline, now)
        deadline_status = self._deadline_status(status=status, days_until=days_until)
        urgency = self._urgency(status=status, deadline_status=deadline_status, days_until=days_until)
        next_action = self._next_action(
            status=status,
            deadline_status=deadline_status,
            days_until=days_until,
            existing=getattr(application, "next_action", None),
        )
        role = getattr(job, "title", None) or "this role"
        company = getattr(job, "company", None) or "the company"
        summary = self._summary(
            role=role,
            company=company,
            status=status,
            deadline_status=deadline_status,
            days_until=days_until,
            next_action=next_action,
        )
        return ApplicationTrackingInsight(
            application_id=getattr(application, "id", ""),
            status=status,
            deadline_status=deadline_status,
            days_until_deadline=days_until,
            urgency=urgency,
            next_action=next_action,
            summary=summary,
        ).to_dict()

    def brief(self, rows: Iterable[Any]) -> Dict[str, Any]:
        insights: List[Dict[str, Any]] = []
        counts: Dict[str, int] = {}
        for row in rows:
            if isinstance(row, tuple):
                application, job = row[0], row[1] if len(row) > 1 else None
            else:
                application, job = row, None
            insight = self.inspect_application(application, job)
            insights.append(insight)
            counts[insight["status"]] = counts.get(insight["status"], 0) + 1

        ordered = sorted(
            insights,
            key=lambda item: (
                self._urgency_rank(item["urgency"]),
                item["days_until_deadline"] if item["days_until_deadline"] is not None else 9999,
                STATUS_ORDER.get(item["status"], 50),
            ),
        )
        overdue = sum(1 for item in insights if item["deadline_status"] == "overdue")
        due_soon = sum(1 for item in insights if item["deadline_status"] == "due_soon")
        active = sum(1 for item in insights if item["status"] not in TERMINAL_STATUSES)
        headline = self._headline(active=active, overdue=overdue, due_soon=due_soon)
        return {
            "headline": headline,
            "active_count": active,
            "overdue_count": overdue,
            "due_soon_count": due_soon,
            "status_counts": counts,
            "next_focus": ordered[:5],
            "generated_at": datetime.utcnow(),
        }

    def _days_until(self, deadline: Optional[datetime], now: datetime) -> Optional[int]:
        if deadline is None:
            return None
        return (deadline.date() - now.date()).days

    def _deadline_status(self, status: str, days_until: Optional[int]) -> str:
        if status in TERMINAL_STATUSES:
            return "closed"
        if days_until is None:
            return "unscheduled"
        if days_until < 0:
            return "overdue"
        if days_until <= 3:
            return "due_soon"
        return "scheduled"

    def _urgency(self, status: str, deadline_status: str, days_until: Optional[int]) -> str:
        if status in TERMINAL_STATUSES:
            return "low"
        if deadline_status == "overdue":
            return "critical"
        if deadline_status == "due_soon":
            return "high"
        if days_until is not None and days_until <= 7:
            return "medium"
        if status in {"generated", "applied", "interviewing"}:
            return "medium"
        return "low"

    def _next_action(
        self,
        status: str,
        deadline_status: str,
        days_until: Optional[int],
        existing: Optional[str],
    ) -> str:
        if existing and deadline_status not in {"overdue", "due_soon"}:
            return existing
        if deadline_status == "overdue":
            return "Review immediately: either submit, extend the deadline, or close this application."
        if deadline_status == "due_soon":
            return "Prioritize this application and complete the next step before the deadline."
        if status == "saved":
            return "Decide whether to generate documents or archive the role."
        if status == "generated":
            return "Review generated documents and submit the application."
        if status == "applied":
            return "Schedule a follow-up reminder and watch for recruiter replies."
        if status == "interviewing":
            return "Prepare interview notes and confirm the next interview date."
        if status == "offer":
            return "Review offer terms and decide whether to accept, negotiate, or decline."
        if status == "rejected":
            return "Capture lessons learned and close the loop."
        if status == "withdrawn":
            return "No action needed unless you want to revisit this role."
        return "Choose the next concrete application step."

    def _summary(
        self,
        role: str,
        company: str,
        status: str,
        deadline_status: str,
        days_until: Optional[int],
        next_action: str,
    ) -> str:
        if deadline_status == "overdue":
            timing = f"deadline passed {abs(days_until or 0)} day(s) ago"
        elif days_until is None:
            timing = "no deadline set"
        elif days_until == 0:
            timing = "deadline is today"
        else:
            timing = f"deadline in {days_until} day(s)"
        return f"{role} at {company} is {status} with {timing}. {next_action}"

    def _headline(self, active: int, overdue: int, due_soon: int) -> str:
        if overdue:
            return f"{overdue} application(s) need immediate deadline attention."
        if due_soon:
            return f"{due_soon} application(s) are due soon."
        if active:
            return f"{active} active application(s) are on track."
        return "No active applications need attention."

    def _urgency_rank(self, urgency: str) -> int:
        return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(urgency, 4)
