# 5-minute demonstration script

1. **Introduce the problem (30 sec):** A room outage can invalidate a timetable. CampusFlow AI creates a legal schedule and repairs it with minimum disruption.
2. **Show the data (45 sec):** Open Rooms & labs and Sessions. Point out capacity, facilities, availability, duration, allowed start times, and priority.
3. **Generate (45 sec):** Click Generate timetable. Explain that each session is a CSP variable and each room/start-time pair is a domain value.
4. **Explain the search (60 sec):** MRV chooses the most constrained session first; LCV tries choices that leave other sessions with more options; backtracking undoes failed choices.
5. **Cause a disruption (60 sec):** Select Lab A and apply the outage. Compare the old and repaired timetable and inspect which sessions moved.
6. **Validate (30 sec):** Explain that the result is checked against hard constraints and that an infeasible result is reported honestly.
7. **Close (30 sec):** Discuss the repair cost, priority weighting, search limits, and how the project maps to search techniques and CSPs in the AI syllabus.
