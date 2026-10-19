"""Objective function for minimum-change timetable repair."""
from .models import Session, Assignment


def assignment_cost(session: Session, old: Assignment | None, new: Assignment) -> int:
    """Return 0 if unchanged; otherwise penalize moving high-priority sessions more."""
    if old is None:
        return 0
    if old.room_id == new.room_id and old.start_slot == new.start_slot:
        return 0
    # Priority is clamped to 1..5 to keep cost predictable and explainable.
    priority = max(1, min(5, session.priority))
    return 10 * priority + (5 if old.start_slot != new.start_slot else 0) + (2 if old.room_id != new.room_id else 0)


def total_repair_cost(
    sessions: list[Session], old_schedule: dict[str, Assignment],
    new_schedule: dict[str, Assignment],
) -> int:
    by_id = {session.id: session for session in sessions}
    return sum(
        assignment_cost(by_id[sid], old_schedule.get(sid), assignment)
        for sid, assignment in new_schedule.items() if sid in by_id
    )
