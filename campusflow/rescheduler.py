"""Disruption handling and minimum-change repair search."""
from __future__ import annotations
from dataclasses import dataclass
from .models import Room, Session, Assignment
from .constraints import validate_schedule
from .scheduler import build_domains, _compatible
from .optimizer import assignment_cost, total_repair_cost


@dataclass
class RepairResult:
    schedule: dict[str, Assignment] | None
    cost: int | None
    moved_sessions: list[str]
    nodes: int
    optimality_proven: bool
    message: str


def repair_schedule(
    rooms: list[Room], sessions: list[Session], slots: list[str],
    old_schedule: dict[str, Assignment], unavailable_rooms: set[str],
    node_limit: int = 250_000,
) -> RepairResult:
    """Find a valid repair minimizing weighted changes, subject to a node limit."""
    invalid = validate_schedule(rooms, sessions, old_schedule, slots, unavailable_rooms)
    # A disruption intentionally makes old assignments invalid; all other old-schedule
    # errors are allowed to be repaired by the same search.
    domains = build_domains(rooms, sessions, slots, unavailable_rooms)
    no_domain = [s.name for s in sessions if not domains.get(s.id)]
    if no_domain:
        return RepairResult(None, None, [], 0, True,
                            "Repair is infeasible. No legal room/time option remains for: " + ", ".join(no_domain) + ".")
    room_by_id = {r.id: r for r in rooms}
    session_by_id = {s.id: s for s in sessions}
    schedule: dict[str, Assignment] = {}
    best: dict[str, Assignment] | None = None
    best_cost = float("inf")
    nodes = 0
    stopped = False

    def options_for(session: Session) -> list[Assignment]:
        legal = [a for a in domains[session.id] if _compatible(
            session, a, rooms, sessions, schedule, slots, unavailable_rooms
        )]
        old = old_schedule.get(session.id)
        legal.sort(key=lambda a: (
            assignment_cost(session, old, a),
            a.start_slot != (old.start_slot if old else None),
            a.room_id != (old.room_id if old else None),
            a.start_slot, a.room_id,
        ))
        return legal

    def recurse(current_cost: int) -> None:
        nonlocal nodes, best, best_cost, stopped
        if len(schedule) == len(sessions):
            if current_cost < best_cost:
                issues = validate_schedule(rooms, sessions, schedule, slots, unavailable_rooms)
                if not issues:
                    best, best_cost = dict(schedule), current_cost
            return
        if nodes >= node_limit:
            stopped = True
            return
        choices = []
        for session in sessions:
            if session.id not in schedule:
                opts = options_for(session)
                if not opts:
                    return
                choices.append((len(opts), -session.priority, session.id, session, opts))
        _, _, _, current, opts = min(choices, key=lambda x: (x[0], x[1], x[2]))
        for candidate in opts:
            nodes += 1
            extra = assignment_cost(current, old_schedule.get(current.id), candidate)
            if current_cost + extra >= best_cost:
                continue
            schedule[current.id] = candidate
            recurse(current_cost + extra)
            del schedule[current.id]
            if stopped:
                return

    recurse(0)
    if best is None:
        if stopped:
            return RepairResult(None, None, [], nodes, False,
                                f"Search limit ({node_limit:,} nodes) reached before a valid repair was found.")
        return RepairResult(None, None, [], nodes, True,
                            "No valid repair exists under the current constraints.")
    moved = [
        s.name for s in sessions
        if s.id in old_schedule and (
            old_schedule[s.id].room_id != best[s.id].room_id
            or old_schedule[s.id].start_slot != best[s.id].start_slot
        )
    ]
    return RepairResult(
        best, int(best_cost), moved, nodes, not stopped,
        "Lowest-cost repair proven." if not stopped else "Valid best-known repair found; search limit reached, so optimality is not proven."
    )
