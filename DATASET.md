# DATASET.md — the screenplay (dummy data)

This is authored for **drama, not realism**. The shipments are positioned so that *one* injected disruption produces three different, defensible decisions. It's a screenplay, not a database. Claude Code should turn this into the JSON files in `data/`.

## Chokepoints

Points a route can pass through. Risk events attach to a chokepoint.

| id | name | type |
|---|---|---|
| HAM | Port of Hamburg | seaport |
| RTM | Port of Rotterdam | seaport |
| ANR | Port of Antwerp | seaport |
| SUEZ | Suez Canal | canal |
| REDSEA | Red Sea / Bab-el-Mandeb | strait |
| COGH | Cape of Good Hope | ocean route |
| RHINE | Rhine barge corridor | inland waterway |

## Candidate routes

Each shipment has a **primary** route and one or more **alternates**. Each route lists the chokepoints it passes and rough transit/cost so the Route Advisor can weigh trade-offs. `cost_index` is relative (100 = baseline), not real money.

| route_id | description | discharge_port | inland leg | transit_days | cost_index | chokepoints |
|---|---|---|---|---|---|---|
| R-HAM-STD | Asia → Suez → Hamburg | HAM | rail/road ex-Hamburg | 32 | 100 | SUEZ, REDSEA, HAM |
| R-RTM-ALT | Asia → Suez → Rotterdam | RTM | road ex-Rotterdam | 34 | 108 | SUEZ, REDSEA, RTM |
| R-RTM-STD | Asia → Suez → Rotterdam (native) | RTM | road ex-Rotterdam | 33 | 100 | SUEZ, REDSEA, RTM |
| R-ANR-STD | Asia → Suez → Antwerp | ANR | road ex-Antwerp | 33 | 100 | SUEZ, REDSEA, ANR |
| R-COGH-ALT | Asia → Cape of Good Hope → Hamburg | HAM | rail/road ex-Hamburg | 42 | 130 | COGH, HAM |

## The 5 shipments (the board)

Authored so the injected Hamburg strike splits them 2 reroute / 1 hold / 2 green.

| id | cargo | origin → final | primary route | alternates | deadline_slack_days | notes |
|---|---|---|---|---|---|---|
| SHP-001 | Automotive parts | Shanghai → Munich | R-HAM-STD | R-RTM-ALT | 4 | Comfortable slack. Clean reroute candidate. |
| SHP-002 | Refrigerated pharma (reefer) | Ningbo → Hamburg | R-HAM-STD | (none good) | 1 | Cold chain, tight, final customer *is* in Hamburg — reroute makes it worse. |
| SHP-003 | Furniture | Shanghai → Rotterdam | R-RTM-STD | — | 3 | Bound for Rotterdam. Does not touch Hamburg. |
| SHP-004 | Electronics | Shenzhen → Antwerp | R-ANR-STD | — | 2 | Bound for Antwerp. Unaffected. |
| SHP-005 | Machinery | Busan → Hamburg | R-HAM-STD | R-RTM-ALT | 3 | Slack absorbs the +2 days of the Rotterdam alternate. Second reroute. |

### Expected decisions on the injected strike (this is the payoff)

- **SHP-001 → REROUTE** to R-RTM-ALT. *Reasoning:* strike blocks HAM ~3–5 days; the Rotterdam alternate adds only 2 days; 4 days of slack absorbs it. Faster than waiting out the strike.
- **SHP-005 → REROUTE** to R-RTM-ALT. Same logic; 3 days slack ≥ the 2-day penalty.
- **SHP-002 → HOLD + NOTIFY.** *Reasoning:* customer is in Hamburg, so Rotterdam adds road transit *and* a cold-chain transfer for a tight, temperature-sensitive load — worse than waiting. Recommend holding at anchorage with the reefer powered, and notifying the customer of a likely short delay. **This "no good option, here's the least-bad one" call is what shows judgment — make its reasoning explicit.**
- **SHP-003 → NO ACTION.** Bound for Rotterdam; strike doesn't touch its route. Stays green.
- **SHP-004 → NO ACTION.** Bound for Antwerp; unaffected. Stays green.

> Start with 4 shipments (drop SHP-005) if you want the simplest clean demo. Add SHP-005 back to show "it triages the whole board, not a one-off."

## The injected disruption (the scripted event)

This is the button-triggered event. It uses the **same format as live events** so it flows through the real pipeline.

```
event_id: EVT-HAM-STRIKE
chokepoint: HAM
type: strike
severity: high
title (DE): "Warnstreik im Hamburger Hafen — ver.di ruft zu ganztägigem Ausstand auf"
title (EN, for display): "Warning strike at Port of Hamburg — union calls full-day walkout"
expected_duration_hours: 48–72
source_language: de
detected_first_from: German-language RSS (e.g. NDR / tagesschau / union press)
english_wire_lag: ~1 day
```

**The earliness story:** the Risk Monitor's German feed catches `Warnstreik Hamburger Hafen` before the English wires carry it. In the demo you point out the source language — that *is* the differentiation, made visible.

## Making the live half real (so "is this real?" has a true answer)

While the strike above is injected, the Risk Monitor should be **genuinely pulling live data** in parallel, across all six families and including at least one non-English feed. The exact sources live in **DATA-SOURCES.md**, so this file and the source list never drift apart.

The live pull is what earns credibility. The injected strike is what makes the demo happen on command. Both are honest as long as you say which is which.
