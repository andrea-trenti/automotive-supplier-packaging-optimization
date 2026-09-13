# FINAL QA REPORT

## Release verdict

**PASS - ready for final packaging.**

The final release was closed without adding new routing, forecasting or optimization algorithms. The closure focused on rerun stability, financial and emissions reconciliation, returnable conservation, service-tail transparency, documentation consistency and archive integrity.

## Core rerun stability

| Check | Reconciled result | Status |
|---|---:|---|
| Smart Baseline B | EUR 52.92M/year | PASS |
| Nominal joint | EUR 47.86M/year | PASS |
| Robust Target+ | EUR 47.98M/year | PASS |
| Robust saving vs B | 9.33% | PASS |
| Robustness premium | 0.26% | PASS |
| Target+ routes | 57 | PASS |
| MILP gap | 1.019e-15 | PASS |

The rerun reproduced the same selected Target+ candidate and the same policy comparison values used in the final thesis.

## Service and tail-risk consistency

Target+ nominal critical fill rate is **99.9991%**. This does **not** imply zero production interruption: P(at least one line stop) is **6.7%** in the nominal core evaluation.

Out of sample, Target+ critical fill is **99.9046%** and P(at least one line stop) is **48.0%**. The corresponding nominal-policy OOS line-stop probability is **87.3%**.

Under combined stress, Target+ critical fill is **97.34%** and line-stop probability is **100%**. This failure region remains visible in the README and thesis.

## Cost reconciliation

The following components are reconciled independently to TLC for every policy:

`transport + packaging material + cleaning/repair + reverse logistics + inventory + handling + damage + dock wait + dock overtime + premium freight + line-stop exposure`.

Maximum absolute reconciliation residual across policies: **EUR 0.000000**.

The cost bridge between Baseline B and Target+ also sums to the exact TLC difference within floating-point tolerance. Savings attribution is explicitly labeled accounting attribution, not causal Shapley attribution.

## Physical feasibility

- Payload <= vehicle payload: PASS.
- Cube <= usable cube: PASS.
- Pallet positions <= vehicle capacity: PASS.
- Route feasibility flags: PASS.
- Frequency >= physical minimum: PASS.
- Route-validation issues: 0.
- Dock wait >= 0 and service times ordered: PASS.

## Returnable audit

- Theoretical fleet: **129,888**.
- Operational fleet: **150,272**.
- Operational >= theoretical for every returnable part: PASS.
- Closed-loop state conservation across **95,220 part-day states**: PASS.
- Lost containers are explicit and non-negative: PASS.
- Median returnable/expendable break-even: **69.4 cycles**.

## CO2 reconciliation

Transport CO2e is activity based:

`annual kgCO2e = tonne-km/trip x WTW gCO2e/t-km x annual trips / 1000`.

Maximum row-level formula residual: **1.455e-11 kgCO2e**.

Target+ changes transport emissions by **-13.8% vs Baseline B** but **+0.3% vs Baseline A**. No generic statement that optimization always reduces emissions is used.

Packaging-lifecycle emissions remain a synthetic proxy and are kept separate from ISO/GLEC transport accounting.

## Resilience audit

- Main tail-risk combination: **carrier capacity + demand shock + container availability**.
- TTS < TTR suppliers: **28**.
- Maximum TTR - TTS gap: **5.73 days**.
- Target+ combined-stress critical fill remains below the normal service requirement, so resilience limitations are not hidden.

## Financial audit

- Monte Carlo draws: **4,096**.
- NPV P5: **EUR 3.15M**.
- NPV P50: **EUR 6.39M**.
- NPV P95: **EUR 9.49M**.
- Median payback: **2.39 years**.
- P(NPV > 0): **100% within the synthetic modeled range**.

**Important:** P(NPV > 0) = 100% inside the synthetic uncertainty range is not industrial certainty. It only means the specified synthetic uncertainty distribution does not cross the zero-NPV boundary.

## Automated tests

Final suite: **42 passed, 0 failed**.

Closure coverage includes unit conversions, TLC reconciliation, CO2 units, payload/cube/pallet capacity, returnable conservation, OOS policy comparison, chance-service evaluation, combined-stress visibility and probabilistic-finance sample integrity.

## Credibility boundary

This is a research-grade synthetic engineering study, not a Ferrari/OEM data model, not a plant-calibrated forecast and not a digital twin. The main remaining uncertainty is empirical validity, not missing algorithm count.

## Final decision statement

> A robust 9% saving against a credible baseline is much stronger than a fragile 40% saving against a weak baseline.

## PDF visual verification

The final Technical Thesis PDF contains **16 A4 pages**. It was rendered to PNG at 160 dpi and visually inspected as a contact sheet plus full-size inspection of the dense OOS/stress/ablation appendix page. No clipped text, figure overflow, table truncation, missing glyphs or overlapping page elements were observed.

## README / thesis consistency

The README, thesis, `outputs/final_summary.json`, `data/processed/policy_comparison.csv`, OOS results, stress suite, returnable audit and probabilistic NPV all use the same reconciled release numbers. The 40.2% result appears only as the falsified weak-baseline result, never as the final headline.

## Archive protocol

The repository includes a SHA-256 manifest of internal release files. FULL and GITHUB archives are created only after this QA report, caches/build directories are excluded, and each archive is checked with `unzip -t`. Archive-level SHA-256 hashes are reported externally with the deliverables because an archive cannot contain its own final hash without changing that hash.

## Final archive integrity execution

Final packaging was executed after all documentation and tests were frozen. Both `automotive-supplier-packaging-optimization-FULL.zip` and `automotive-supplier-packaging-optimization-GITHUB.zip` were checked with `unzip -t`; both returned **No errors detected in compressed data**. Archive-level SHA-256 values are reported alongside the downloadable artifacts.

## Public GitHub distribution smoke test

The recruiter-facing GitHub package was re-tested after final presentation pruning. It passes **42/42 tests** without requiring the omitted multi-megabyte `returnable_state_history.csv` or raw `probabilistic_npv.csv` artifacts: the two corresponding closure tests now recreate deterministic in-memory checks from the frozen model inputs. This preserves the public package's verification coverage while keeping reproducible raw simulation state out of the distribution.

Portfolio polish changed presentation and distribution only; no routing, forecasting or optimization methodology was added and none of the reconciled scientific results changed.

## Public-package hardening audit

The final GitHub distribution was re-audited after portfolio pruning. All 42 tests now reference current final-release artifacts rather than Part-1 alias outputs. Obsolete Part-1 runners, duplicate processed aliases, bytecode/cache files and superseded summary artifacts were removed from the public distribution only; the scientific results, FULL archive and Technical Thesis PDF were not changed. README links and all nine PNG figures were validated from the extracted ZIP.

The final public package therefore preserves evidence and reproducibility while avoiding a parallel legacy-output path that could confuse reviewers.
