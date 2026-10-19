# Architecture

## Layering
- `app.py` is the Streamlit presentation layer. It validates user input at the boundary, invokes domain functions, and renders results.
- `models.py` contains immutable `Room`, `Session`, and `Assignment` models.
- `constraints.py` is the single source of truth for hard-constraint checks and independent final validation.
- `scheduler.py` builds session domains and runs backtracking with MRV and LCV heuristics.
- `optimizer.py` defines the soft objective for a repair.
- `rescheduler.py` searches for a valid post-disruption allocation and minimizes weighted changes.
- `sample_data.py` provides a repeatable demo dataset; `storage.py` provides optional JSON persistence helpers.

## Data model
A room contains an ID, display name, capacity, facility labels, and available slots. A session contains an ID, name, number of students, duration in consecutive slots, required facilities, allowed start slots, and priority. An assignment binds a session ID to a room ID and start slot.

## Search flow
1. Build each session's initial domain by filtering room/start-slot pairs against individual hard constraints.
2. Pick the unassigned session with the smallest current legal domain (MRV).
3. Order candidate values by how many options they leave to the remaining variables (LCV).
4. Add a candidate assignment and recurse; remove it when a downstream conflict makes the branch impossible.
5. Independently validate the completed schedule before returning it.

## Repair objective
For each existing session:
- unchanged room and start time: cost 0;
- moved session: `10 × clamped priority`;
- additionally add 5 when start time changes and 2 when room changes.

The objective is applied only among hard-constraint-valid schedules. The search reports whether it completed or stopped at the node limit, so a feasible answer is not falsely advertised as a proven global optimum.

## Complexity
Backtracking is exponential in the worst case. MRV/LCV improve practical search order but do not change the worst-case complexity class. The node limit bounds the amount of work in the UI. The initial demo uses 6 rooms and 12 sessions.
