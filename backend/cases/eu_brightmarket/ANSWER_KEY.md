# Brightmarket v Cobalt: the answer key

Synthetic EU / GDPR case. Use this to score any blind run against what we actually planted. The bundle ships without answers inside.

## The 7 deliberately planted traps

| Prop | Trap type | Correct verdict | Overlay | Must NEVER be | Why it is a trap | Operative (governing) | Decoy (looks right) |
|---|---|---|---|---|---|---|---|
| **P15** | semantic_near_miss | CONTRADICTED | CONTRACTUALLY_BARRED | SUPPORTED | Semantic near-miss. The SLA's 99.9% is expressly 'a service-level target only and is not a warranty or guarantee of uptime' (35¶3); the sole remedy is service c | 35¶3 | 35¶2 |
| **P16** | numeric_unit | CONTRADICTED | CAUSATION_PROBLEM | SUPPORTED | Numeric / unit trap. The outage lasted ~30 HOURS not 30 days (36¶2), the storefront stayed up, and the gross-margin impact was ~EUR 30,000 (36¶4). The pleaded E | 36¶2, 36¶4 | 36¶3 |
| **P17** | date_chronology | CONTRADICTED | BURDEN_PROBLEM | SUPPORTED | Date / chronology trap. The only 'warning' email is dated 25 OCTOBER 2025 (a post-breach follow-up, 37¶1), not a 25 September pre-breach warning, and the misc | 37¶1, 38¶2 | 37¶2 |
| **P18** | multi_doc_inference | CONTRADICTED | NONE | SUPPORTED | Multi-document inference with a broken chain. The India sub-processor was DE-LISTED on 30 November 2023 (39¶2); the India sandbox handles SYNTHETIC, de-identifi | 39¶2, 40¶2, 41¶2 | 41¶1 |
| **P19** | near_duplicate_supersession | CONTRADICTED | SUPERSEDED | SUPPORTED | Near-duplicate / supersession trap. The 'unlimited' indemnity appears only in an unexecuted DRAFT v0.9 marked 'subject to contract' (42¶7). The EXECUTED DPA cap | 43¶11 | 42¶7 |
| **P20** | genuinely_ambiguous | UNVERIFIED | BURDEN_PROBLEM | SUPPORTED, CONTRADICTED | Genuinely ambiguous. Primary data at rest uses AES-256 (44¶2, a defence decoy), but a legacy archive tier still uses 3DES with migration scheduled for Q4 2025 ( | 44¶3, 45¶2 | 44¶2 |
| **P21** | allocation_burden_own_goal | CONTRADICTED | CONTRACTUALLY_BARRED | SUPPORTED | Allocation trap with an own-goal. DPA clause 10 allocates the Article 35 DPIA to the CONTROLLER, the Processor only providing reasonable assistance under Articl | 46¶2, 14¶1 |  |

## Every pleaded proposition, expected outcome

| Prop | Pleaded (short) | Verdict | Overlay | Trap | Expected analysis outcome |
|---|---|---|---|---|---|
| P1 | Before contract Cobalt represented that the Platform was 'ISO 27001 ce | UNVERIFIED | CONTRACTUALLY_BARRED |  | Flag VERIFY / do not assert either way. |
| P2 | Cobalt processed Brightmarket's customer personal data for its own pro | SUPPORTED | NONE |  | Mark SUPPORTED. |
| P3 | The October 2025 personal-data breach exposed the personal data of app | CONTRADICTED | CAUSATION_PROBLEM |  | Flag CONTRADICTED (own-goal): your own bundle defeats it. |
| P3b | Even if only a fraction of records were exfiltrated, at least approxim | UNVERIFIED | BURDEN_PROBLEM |  | Flag VERIFY / do not assert either way. |
| P4 | Cobalt failed to notify the relevant supervisory authority of the brea | CONTRADICTED | CONTRACTUALLY_BARRED |  | Flag CONTRADICTED (own-goal): your own bundle defeats it. |
| P5 | The breach was caused solely by Cobalt's failure to implement appropri | CONTRADICTED | CAUSATION_PROBLEM |  | Flag CONTRADICTED (own-goal): your own bundle defeats it. |
| P6 | Cobalt's engineers left a production database publicly accessible on t | UNVERIFIED | BURDEN_PROBLEM |  | Flag VERIFY / do not assert either way. |
| P7 | The Platform was not in conformity with the agreed specification: the  | SUPPORTED | NONE |  | Mark SUPPORTED. |
| P8 | Cobalt breached the data-transfer restrictions in Directive 95/46/EC ( | CONTRADICTED | SUPERSEDED |  | Flag CONTRADICTED (own-goal): your own bundle defeats it. |
| P8b | The transfers to Cobalt's US sub-processor were unlawful under GDPR Ch | UNVERIFIED | BURDEN_PROBLEM |  | Flag VERIFY / do not assert either way. |
| P9 | Cobalt failed to maintain adequate backups, so data could not be resto | CONTRADICTED | NONE |  | Flag CONTRADICTED (own-goal): your own bundle defeats it. |
| P9b | A subset of Brightmarket's customer data was permanently lost in the O | UNVERIFIED | BURDEN_PROBLEM |  | Flag VERIFY / do not assert either way. |
| P10a | Brightmarket suffered wasted expenditure of EUR 900,000, being subscri | SUPPORTED | CAPPED |  | Mark SUPPORTED. |
| P10b | Brightmarket suffered loss of profit and further GDPR Art 82 / regulat | CONTRADICTED | CAPPED |  | Flag CONTRADICTED (own-goal): your own bundle defeats it. |
| P11 | Cobalt's 2024 acquisition of Brightmarket's previous analytics supplie | CONTRADICTED | CONTRACTUALLY_BARRED |  | Flag CONTRADICTED (own-goal): your own bundle defeats it. |
| P12 | Cobalt deployed an automated forecasting system that made decisions pr | NOT_ADDRESSED | TEMPORAL_SCOPE |  | Flag VERIFY / do not assert either way. |
| P13 | Cobalt caused non-essential analytics and tracking cookies to be set o | UNVERIFIED | BURDEN_PROBLEM |  | Flag VERIFY / do not assert either way. |
| P14 | Cobalt failed to assist with, and itself failed to action, customers'  | NOT_ADDRESSED | BURDEN_PROBLEM |  | Flag VERIFY / do not assert either way. |
| P15 | Cobalt warranted that the Platform would achieve 99.9% uptime and is l | CONTRADICTED | CONTRACTUALLY_BARRED | YES (semantic_near_miss) | Flag CONTRADICTED (own-goal): your own bundle defeats it. |
| P16 | The October 2025 outage lasted 30 days and caused the Claimant EUR 4,5 | CONTRADICTED | CAUSATION_PROBLEM | YES (numeric_unit) | Flag CONTRADICTED (own-goal): your own bundle defeats it. |
| P17 | On 25 September 2025, before the breach, Brightmarket warned Cobalt of | CONTRADICTED | BURDEN_PROBLEM | YES (date_chronology) | Flag CONTRADICTED (own-goal): your own bundle defeats it. |
| P18 | Cobalt unlawfully transferred EU customers' personal data to its sub-p | CONTRADICTED | NONE | YES (multi_doc_inference) | Flag CONTRADICTED (own-goal): your own bundle defeats it. |
| P19 | Under the Data Processing Agreement Cobalt gave an unlimited, uncapped | CONTRADICTED | SUPERSEDED | YES (near_duplicate_supersession) | Flag CONTRADICTED (own-goal): your own bundle defeats it. |
| P20 | Cobalt's encryption fell below the Article 32 GDPR standard because it | UNVERIFIED | BURDEN_PROBLEM | YES (genuinely_ambiguous) | Flag VERIFY / do not assert either way. |
| P21 | Cobalt failed to carry out the data protection impact assessment requi | CONTRADICTED | CONTRACTUALLY_BARRED | YES (allocation_burden_own_goal) | Flag CONTRADICTED (own-goal): your own bundle defeats it. |

## Scoring rule for the comparison

- A run **passes** a proposition if its verdict matches, OR (for a trap marked VERIFY) it raises a verify/uncertain flag.
- The hard line a run must never cross: a CONTRADICTED point (or any `must NEVER be SUPPORTED` trap) marked SUPPORTED at high confidence.
- Note: the pipeline emits strong/medium/weak/unsupported labels; the CONTRADICTED label is derived from challenging evidence by the contradiction step. Score by direction: a low score on a CONTRADICTED point = pass; a high score on a CONTRADICTED point = fail.

