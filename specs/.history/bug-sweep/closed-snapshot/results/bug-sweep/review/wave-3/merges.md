# Milestone 1 merges (waves 1–3), epic/bug-sweep

Range: df48724c (kickoff plan) → 45575a43. Squash-merged by the epic agent, DCO sign-off on each.

| Planned order | Ticket | Issue | PR | Merge SHA | Actual position | Note |
|---|---|---|---|---|---|---|
| 10 | BS-09 | #194 | #204 | acba8ad2 | 1 | |
| 20 | BS-03 | #175 | #176 | 5748dcc6 | 2 | PR retargeted from main; merged epic tip in (no rebase) |
| 30 | BS-01 | #187 | #208 | a94f0a82 | 3 | plan-anchor fix 933bfcad landed by the epic agent just before |
| 40 | BS-02 | #188 | #206 | d5c8bbaa | 4 | |
| 50 | BS-04 | #189 | #205 | 6cf7f653 | 5 | |
| 110 | BS-22 | #200 | #207 | 29e73819 | 6 | **early**: disjoint keys; unblocked BS-12 |
| 90 | BS-10 | #195 | #209 | 02375b14 | 7 | **early** vs BS-05..07 (disjoint keys) |
| 60 | BS-05 | #190 | #210 | f21fd11c | 8 | |
| 70 | BS-06 | #191 | #211 | edd8d5d0 | 9 | |
| 100 | BS-20 | #202 | #212 | 0bb9a950 | 10 | before BS-07 (disjoint keys) |
| 80 | BS-07 | #192 | #213 | bc926c4e | 11 | |
| 140 | BS-12 | #141 | #214 | a4d2cde4 | 12 | wave 2 before wave-1 BS-08 (no dependency) |
| 150 | BS-19 | #201 | #215 | 1262f7e6 | 13 | |
| 130 | BS-11 | #185 | #216 | d9c20ee4 | 14 | |
| 190 | BS-21 | #203 | #217 | da6ab2f7 | 15 | **early** vs BS-15 (BS-15 stayed off close_tickets.py) |
| 170 | BS-14 | #147 | #218 | abfcbc3c | 16 | |
| 180 | BS-15 | #148 | #219 | 3b42f188 | 17 | |
| 160 | BS-13 | #186 | #220 | 54ec4a34 | 18 | |
| 120 | BS-08 | #193 | #221 | 45575a43 | 19 | promoted last on purpose (merged every other fix first) |

The lane did not hold strictly: tickets merged as they finished, never two at once, and only where conflict keys were disjoint and every `depends_on` was already merged. Zero merge conflicts across 19 PRs.

| BS-23 | #222 | #223 | 90d4538f | wave 4, added at schedule revision 2 (owner request); docs only |
