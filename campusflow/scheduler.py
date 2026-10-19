"""CSP scheduler using backtracking, MRV, and least-constraining-value ordering."""
from __future__ import annotations
from dataclasses import dataclass
from .models import Room, Session, Assignment
from .constraints import candidate_is_valid, occupied_slots, validate_schedule


@dataclass
class SearchResult:
    schedule: dict[str, Assignment] | None
    nodes: int
    complete: bool
    message: str


def build_domains(
    rooms: list[Room], sessions: list[Session], slots: list[str],
    unavailable_rooms: set[str] | None = None,
) -> dict[str, list[Assignment]]:
    unavailable_rooms = unavailable_rooms or set()
    domains: dict[str, list[Assignment]] = {}
    for session in sessions:
        options: list[Assignment] = []
        for room in rooms:
            for start in session.allowed_start_slots:
                if candidate_is_valid(session, room, start, rooms, sessions, {}, slots, unavailable_rooms):
                    options.append(Assignment(session.id, room.id, start))
        domains[session.id] = options
    return domains


def _compatible(
    session: Session, candidate: Assignment, rooms: list[Room], sessions: list[Session],
    schedule: dict[str, Assignment], slots: list[str], unavailable_rooms: set[str],
) -> bool:
    room_by_id = {room.id: room for room in rooms}
    return candidate_is_valid(
        session, room_by_id[candidate.room_id], candidate.start_slot,
        rooms, sessions, schedule, slots, unavailable_rooms,
    )


def solve_csp(
    rooms: list[Room], sessions: list[Session], slots: list[str],
    unavailable_rooms: set[str] | None = None, node_limit: int = 250_000,
) -> SearchResult:
    """Find the first valid schedule. Uses MRV and least-constraining-value ordering."""
    unavailable_rooms = unavailable_rooms or set()
    if len({s.id for s in sessions}) != len(sessions):
        return SearchResult(None, 0, True, "Session IDs must be unique.")
    if len({r.id for r in rooms}) != len(rooms):
        return SearchResult(None, 0, True, "Room IDs must be unique.")
    domains = build_domains(rooms, sessions, slots, unavailable_rooms)
    empty = [s for s in sessions if not domains[s.id]]
    if empty:
        names = ", ".join(s.name for s in empty)
        return SearchResult(None, 0, True, f"No feasible room/time options for: {names}.")
    by_id = {s.id: s for s in sessions}
    schedule: dict[str, Assignment] = {}
    nodes = 0
    stopped = False

    def options_for(session: Session) -> list[Assignment]:
        return [a for a in domains[session.id] if _compatible(
            session, a, rooms, sessions, schedule, slots, unavailable_rooms
        )]

    def recurse() -> bool:
        nonlocal nodes, stopped
        if len(schedule) == len(sessions):
            return True
        if nodes >= node_limit:
            stopped = True
            return False
        # MRV: choose the unassigned variable with the fewest legal values now.
        choices = []
        for session in sessions:
            if session.id not in schedule:
                options = options_for(session)
                if not options:
                    return False
                choices.append((len(options), -session.priority, session.id, session, options))
        _, _, _, current, options = min(choices, key=lambda x: (x[0], x[1], x[2]))
        # LCV: prefer candidates that leave more options for the remaining sessions.
        def lcv(candidate: Assignment) -> tuple[int, str, str]:
            schedule[current.id] = candidate
            remaining = 0
            for other in sessions:
                if other.id != current.id and other.id not in schedule:
                    remaining += sum(
                        1 for opt in domains[other.id]
                        if _compatible(other, opt, rooms, sessions, schedule, slots, unavailable_rooms)
                    )
            del schedule[current.id]
            return (-remaining, candidate.room_id, candidate.start_slot)
        options.sort(key=lcv)
        for candidate in options:
            nodes += 1
            schedule[current.id] = candidate
            if recurse():
                return True
            del schedule[current.id]
            if stopped:
                return False
        return False

    found = recurse()
    if found:
        issues = validate_schedule(rooms, sessions, schedule, slots, unavailable_rooms)
        if issues:
            return SearchResult(None, nodes, True, "Internal validation failed: " + "; ".join(issues))
        return SearchResult(dict(schedule), nodes, True, "Valid timetable found.")
    if stopped:
        return SearchResult(None, nodes, False, f"Search node limit ({node_limit:,}) reached before finding a solution.")
    return SearchResult(None, nodes, True, "No valid timetable exists for the current constraints.")
