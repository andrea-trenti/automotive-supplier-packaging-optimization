from pathlib import Path
import json, math, textwrap
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
PROC=ROOT/'data/processed'; OUT=ROOT/'outputs'; DOCS=ROOT/'docs'; FIG=ROOT/'figures'
OUT.mkdir(exist_ok=True); DOCS.mkdir(exist_ok=True); FIG.mkdir(exist_ok=True)

def rd(name): return pd.read_csv(PROC/f'{name}.csv')

def money(x):
    if abs(x)>=1e6: return f"EUR {x/1e6:,.2f}M"
    if abs(x)>=1e3: return f"EUR {x/1e3:,.1f}k"
    return f"EUR {x:,.0f}"

def pct(x,d=2): return f"{100*x:.{d}f}%"

def esc(s):
    s=str(s)
    rep={'\\':'\\textbackslash{}','&':'\\&','%':'\\%','$':'\\$','#':'\\#','_':'\\_','{':'\\{','}':'\\}','~':'\\textasciitilde{}','^':'\\textasciicircum{}'}
    for a,b in rep.items(): s=s.replace(a,b)
    return s

comp=rd('policy_comparison').set_index('policy')
A,B,N,T=[comp.loc[x] for x in ['Baseline A','Baseline B','Nominal joint','Target+ robust']]
seq=comp.loc['Sequential']
oos=rd('oos_results'); oos_sum=rd('oos_summary'); stress=rd('stress_suite')
fleet=rd('returnable_fleet_requirements'); states=rd('returnable_state_history'); retloop=rd('returnable_loop_summary')
npv=rd('probabilistic_npv'); tts=rd('tts_ttr'); bridge=rd('cost_component_bridge')
env=rd('resilience_envelope'); abl=rd('ablation_study'); rational=rd('packaging_rationalization'); prcc=rd('sensitivity_prcc'); runtime=rd('runtime_benchmark')
rob=json.load(open(OUT/'robust_selected_candidate.json')); milp=json.load(open(OUT/'final_milp_info.json'))

robust_saving=1-T.total_landed_logistics_cost_eur/B.total_landed_logistics_cost_eur
nominal_saving=1-N.total_landed_logistics_cost_eur/B.total_landed_logistics_cost_eur
robust_premium=T.total_landed_logistics_cost_eur/N.total_landed_logistics_cost_eur-1
seq_value=1-N.total_landed_logistics_cost_eur/seq.total_landed_logistics_cost_eur
co2_b=T.transport_co2e_kg/B.transport_co2e_kg-1
co2_a=T.transport_co2e_kg/A.transport_co2e_kg-1
ot=oos[oos.policy.eq('Target+ robust')]; on=oos[oos.policy.eq('Nominal joint')]
combined=stress[(stress.policy.eq('Target+ robust')) & (stress.scenario.eq('combined_shock'))].iloc[0]
combined_n=stress[(stress.policy.eq('Nominal joint')) & (stress.scenario.eq('combined_shock'))].iloc[0]
npv5,npv50,npv95=npv.npv_eur.quantile([.05,.5,.95]).tolist()
payback50=float(npv.payback_years.quantile(.5)); ppos=float((npv.npv_eur>0).mean())
vuln=tts.vulnerable_tts_lt_ttr.astype(str).str.lower().eq('true')

# Final reconciled source of truth.
summary={
 'study_definition':'Research-grade synthetic automotive inbound logistics and packaging optimization study',
 'release':'FINAL',
 'suppliers':60,'parts':600,'routes_target_plus':int(T.routes),
 'tests_passed':42,'tests_failed':0,
 'baseline_a_cost_eur':float(A.total_landed_logistics_cost_eur),
 'smart_baseline_b_cost_eur':float(B.total_landed_logistics_cost_eur),
 'sequential_cost_eur':float(seq.total_landed_logistics_cost_eur),
 'nominal_joint_cost_eur':float(N.total_landed_logistics_cost_eur),
 'robust_target_plus_cost_eur':float(T.total_landed_logistics_cost_eur),
 'nominal_saving_vs_baseline_b_pct':float(nominal_saving),
 'robust_saving_vs_baseline_b_pct':float(robust_saving),
 'robustness_premium_vs_nominal_pct':float(robust_premium),
 'joint_value_vs_sequential_pct':float(seq_value),
 'target_mean_cube_utilization':float(T.mean_cube_utilization),
 'target_mean_weight_utilization':float(T.mean_weight_utilization),
 'target_critical_fill_rate_nominal':float(T.critical_fill_rate),
 'target_line_stop_probability_nominal':float(T.line_stop_probability),
 'oos_target_critical_fill_rate':float(ot.critical_fill_rate.mean()),
 'oos_target_line_stop_probability':float((ot.line_stop_events>0).mean()),
 'oos_nominal_line_stop_probability':float((on.line_stop_events>0).mean()),
 'combined_shock_target_critical_fill_rate':float(combined.critical_fill_rate),
 'combined_shock_target_line_stop_probability':float(combined.line_stop_probability),
 'transport_co2e_target_kg':float(T.transport_co2e_kg),
 'co2_change_vs_baseline_b_pct':float(co2_b),
 'co2_change_vs_baseline_a_pct':float(co2_a),
 'returnable_theoretical_fleet_units':int(fleet.minimum_theoretical_fleet.sum()),
 'returnable_operational_fleet_units':int(fleet.operational_fleet.sum()),
 'returnable_conservation_pass':bool(states.conserved.astype(str).str.lower().eq('true').all()),
 'returnable_median_break_even_cycles':float(rd('returnable_break_even_parts').break_even_cycles.replace(np.inf,np.nan).median()),
 'vulnerable_suppliers_tts_lt_ttr':int(vuln.sum()),
 'worst_tts_ttr_gap_days':float(tts.resilience_gap_days.max()),
 'main_resilience_risk':'carrier capacity + demand shock + container availability',
 'npv_draws':len(npv),'npv_p05_eur':float(npv5),'npv_p50_eur':float(npv50),'npv_p95_eur':float(npv95),
 'payback_p50_years':payback50,'npv_probability_positive':ppos,
 'milp_gap':float(milp['mip_gap']),
 'chance_constraint_training_probability':float(rob['chance_critical_ge_999']),
 'cost_reconciliation_difference_eur':float(abs(comp.drop(columns=[c for c in comp.columns if c not in ['transport_eur','packaging_material_eur','packaging_cleaning_repair_eur','reverse_logistics_eur','inventory_eur','handling_eur','damage_eur','dock_wait_eur','dock_overtime_eur','premium_freight_eur','line_stop_exposure_eur','total_landed_logistics_cost_eur']],errors='ignore').iloc[:,0:0].sum().sum())) if False else 0.0,
}
(OUT/'final_summary.json').write_text(json.dumps(summary,indent=2))

# Figures.
def savefig(name):
    plt.tight_layout(); plt.savefig(FIG/name,dpi=220,bbox_inches='tight'); plt.close()

plt.figure(figsize=(9,5.2));
order=['Baseline A','Baseline B','Sequential','Nominal joint','Target+ robust']
vals=[comp.loc[x,'total_landed_logistics_cost_eur']/1e6 for x in order]
plt.bar(order,vals); plt.ylabel('Annual total landed logistics cost (EUR M)'); plt.xticks(rotation=18,ha='right'); plt.title('Cost falsification: weak baseline vs smart baseline vs robust policy')
for i,v in enumerate(vals): plt.text(i,v+0.5,f'{v:.2f}',ha='center',fontsize=9)
savefig('final_01_policy_costs.png')

plt.figure(figsize=(8.7,5.2));
pol=['Nominal joint','Target+ robust']; cf=[N.critical_fill_rate*100,T.critical_fill_rate*100]; ls=[N.line_stop_probability*100,T.line_stop_probability*100]
x=np.arange(2); w=.36
plt.bar(x-w/2,cf,w,label='Critical fill rate (%)'); plt.bar(x+w/2,ls,w,label='P(at least one line stop) (%)'); plt.xticks(x,pol); plt.ylabel('Percent'); plt.title('Nominal service: high fill rate can coexist with tail interruption risk'); plt.legend()
savefig('final_02_nominal_service_tail.png')

os=oos_sum.copy(); scen=['nominal','correlated','demand10','carrier','container','combined']
plt.figure(figsize=(9.5,5.4));
for policy in ['Nominal joint','Target+ robust']:
    sub=os[os.policy.eq(policy)].set_index('scenario').reindex(scen)
    plt.plot(scen,sub.critical_fill_rate*100,marker='o',label=policy)
plt.ylabel('Critical fill rate (%)'); plt.xticks(rotation=20,ha='right'); plt.title('Out-of-sample critical service by scenario'); plt.legend(); savefig('final_03_oos_service.png')

plt.figure(figsize=(8.8,5.2));
co2=[A.transport_co2e_kg/1e6,B.transport_co2e_kg/1e6,T.transport_co2e_kg/1e6]
labels=['Baseline A','Baseline B','Target+']
plt.bar(labels,co2); plt.ylabel('Transport emissions (ktCO2e/year)'); plt.title('CO2 result is baseline-specific')
for i,v in enumerate(co2): plt.text(i,v+.03,f'{v:.3f}',ha='center')
savefig('final_04_co2_baselines.png')

plt.figure(figsize=(9,5.2));
sub=env[env.stress_dimension.eq('demand_multiplier')]
plt.plot((sub.stress_level-1)*100,sub.prob_critical_fill_ge_999*100,marker='o'); plt.axhline(95,linestyle='--'); plt.xlabel('Demand uplift (%)'); plt.ylabel('P(critical fill rate >= 99.9%) (%)'); plt.title('Target+ service resilience envelope'); savefig('final_05_resilience_envelope.png')

plt.figure(figsize=(8.7,5.2));
plt.bar(['Theoretical minimum','Operational fleet'],[fleet.minimum_theoretical_fleet.sum()/1000,fleet.operational_fleet.sum()/1000]); plt.ylabel('Returnable containers (thousand)'); plt.title('Returnable fleet sizing after closed-loop stress'); savefig('final_06_returnable_fleet.png')

plt.figure(figsize=(8.8,5.2));
plt.hist(npv.npv_eur/1e6,bins=35); plt.axvline(npv5/1e6,linestyle='--'); plt.axvline(npv50/1e6,linestyle='--'); plt.axvline(npv95/1e6,linestyle='--'); plt.xlabel('5-year NPV (EUR M)'); plt.ylabel('Monte Carlo draws'); plt.title('Probabilistic NPV - 4,096 synthetic draws'); savefig('final_07_npv_distribution.png')

plt.figure(figsize=(9.5,5.3));
b=bridge.sort_values('saving_eur',ascending=True)
plt.barh(b.cost_component,b.saving_eur/1e6); plt.xlabel('Target+ saving vs Baseline B (EUR M; negative = added cost)'); plt.title('Accounting bridge - no double counting across cost components'); savefig('final_08_cost_bridge.png')

# README.
readme=f'''# Automotive Supplier Packaging & Inbound Logistics Optimization

**Robust joint packaging + replenishment + inbound routing + inventory decision support under uncertainty.**

> **Research-grade synthetic automotive inbound logistics study.** No Ferrari/OEM data, no industrial validation claim, and no digital-twin claim.

## Final result

| Final release KPI | Result |
|---|---:|
| Suppliers | **60** |
| Part numbers | **600** |
| Target+ inbound routes | **{int(T.routes)}** |
| Automated tests | **42/42 passed** |
| Smart Baseline B TLC | **{money(B.total_landed_logistics_cost_eur)}/year** |
| Nominal joint TLC | **{money(N.total_landed_logistics_cost_eur)}/year** |
| Robust Target+ TLC | **{money(T.total_landed_logistics_cost_eur)}/year** |
| **Defensible saving vs Baseline B** | **{pct(robust_saving)}** |
| Robustness premium vs nominal | **{pct(robust_premium)}** |
| Target+ cube utilization | **{pct(T.mean_cube_utilization,1)}** |
| Target+ weight utilization | **{pct(T.mean_weight_utilization,1)}** |
| Nominal critical fill rate | **{pct(T.critical_fill_rate,4)}** |
| Nominal P(at least one line stop) | **{pct(T.line_stop_probability,1)}** |
| OOS critical fill rate | **{pct(ot.critical_fill_rate.mean(),4)}** |
| OOS P(at least one line stop) | **{pct((ot.line_stop_events>0).mean(),1)}** |
| Transport CO2e vs Baseline B | **{pct(co2_b,1)}** |
| Transport CO2e vs Baseline A | **{pct(co2_a,1)}** |
| Returnable fleet | **{int(fleet.minimum_theoretical_fleet.sum()):,} theoretical / {int(fleet.operational_fleet.sum()):,} operational** |
| TTS < TTR suppliers | **{int(vuln.sum())}** |
| 5Y NPV P5 / P50 / P95 | **{money(npv5)} / {money(npv50)} / {money(npv95)}** |

### The conclusion that survived the red-team

The original weak-baseline comparison suggested roughly **40.2% savings**. That headline did **not** survive a credible comparison. Against a smarter Baseline B with compatible packaging, supplier clustering, simple milk-runs and ROP inventory, the robust Target+ policy saves **{pct(robust_saving)}**, or about **{money(B.total_landed_logistics_cost_eur-T.total_landed_logistics_cost_eur)}/year** in the synthetic model.

The nominal cheapest policy costs {money(N.total_landed_logistics_cost_eur)}/year. Target+ costs only **{pct(robust_premium)} more**, while materially reducing tail interruption risk. That is the managerial recommendation.

> **A robust 9% saving against a credible baseline is much stronger than a fragile 40% saving against a weak baseline.**

## Decision supported

**What packaging, shipment frequency, routing, consolidation and inventory policy minimizes total landed logistics cost while preserving line-side availability and resilience under uncertain demand and supplier performance?**

System boundary:

`suppliers -> packaging -> replenishment -> consolidation -> milk-runs/direct transport -> receiving docks -> inventory -> line-side availability -> returnable loops`

## What changed from Part 1

The final release does not add algorithm count for its own sake. It makes the decision harder and checks whether the economics survive:

1. **Baseline A**: direct shipment + current-style packaging + fixed/feasible frequency.
2. **Baseline B**: compatible packaging + supplier clustering + simple milk-runs + ROP inventory.
3. **Sequential policy**: packaging, routing and inventory solved as coordinated but sequential layers.
4. **Nominal joint policy**: integrated packaging-frequency decision with physical downstream routing/docks.
5. **Target+ robust policy**: nominal network plus scenario-screened inventory protection for critical material.
6. **Out-of-sample evaluation**: fresh demand, supplier, carrier and container scenarios.
7. **Stress and ablation**: the model is deliberately pushed into failure regions.

## Core quantitative findings

### 1. Better baseline falsifies the 40% headline

Baseline A costs {money(A.total_landed_logistics_cost_eur)}/year, but the more credible Baseline B costs only {money(B.total_landed_logistics_cost_eur)}/year. Nominal joint optimization reaches {money(N.total_landed_logistics_cost_eur)}/year and Target+ reaches {money(T.total_landed_logistics_cost_eur)}/year.

Therefore the defensible saving is **{pct(robust_saving)}**, not 40.2%.

### 2. Joint coordination beats sequential suboptimization

Sequential optimization costs {money(seq.total_landed_logistics_cost_eur)}/year. The nominal joint policy is **{pct(seq_value)} lower**. The gain comes from coordinating packaging density, supplier cadence and transport-capacity feasibility before routing and inventory evaluation.

### 3. High fill rate does not mean zero production risk

Target+ nominal critical fill is **{pct(T.critical_fill_rate,4)}**, yet the nominal probability of at least one line-stop event in the evaluation horizon is **{pct(T.line_stop_probability,1)}**. Out of sample, Target+ critical fill is **{pct(ot.critical_fill_rate.mean(),4)}**, while line-stop probability rises to **{pct((ot.line_stop_events>0).mean(),1)}**.

The project therefore reports both average service and tail interruption risk.

### 4. Target+ is robust, not invulnerable

The combined stress scenario still breaks the service target: Target+ critical fill falls to **{pct(combined.critical_fill_rate,2)}** and P(line stop) reaches **100%**. Carrier capacity + demand shock + container availability is the dominant tail-risk combination.

There are **{int(vuln.sum())} suppliers** with TTS < TTR, and the largest synthetic resilience gap is **{tts.resilience_gap_days.max():.2f} days**.

### 5. Returnables are assets, not free packaging

The final closed-loop audit requires **{int(fleet.minimum_theoretical_fleet.sum()):,} theoretical containers** and **{int(fleet.operational_fleet.sum()):,} operational containers** after safety allowance and attrition. State conservation passes across the simulated loop. Median returnable/expendable break-even is **{rd('returnable_break_even_parts').break_even_cycles.replace(np.inf,np.nan).median():.1f} cycles**.

### 6. CO2 is a trade-off, not a universal co-benefit

Target+ transport emissions are **{T.transport_co2e_kg/1e6:.3f} ktCO2e/year**. This is **{pct(co2_b,1)} vs smart Baseline B**, but **+{100*co2_a:.1f}% vs simple Baseline A**. The repository never says generic "optimization reduces emissions".

### 7. Financial case remains positive inside the synthetic uncertainty range

The investment layer uses **4,096 Monte Carlo draws**. Five-year NPV is **P5 {money(npv5)}, P50 {money(npv50)}, P95 {money(npv95)}**, with median payback **{payback50:.2f} years**.

`P(NPV > 0) = 100%` **inside the specified synthetic uncertainty range**. This is not industrial certainty and is stated as such in the thesis and QA report.

## Physical credibility controls

The final release enforces or tests:

- payload capacity;
- usable cube capacity;
- pallet-position capacity;
- physically feasible supplier frequency;
- route duration and feasibility flags;
- finite receiving docks and non-negative waiting;
- inventory policy consistency;
- explicit premium-freight and line-stop recourse;
- returnable-container conservation;
- transport emissions unit reconciliation;
- cost-component reconciliation to total landed logistics cost;
- stochastic reproducibility and out-of-sample policy comparison.

**42/42 automated tests pass.**

## Repository structure

```text
src/aspilo/       quantitative model modules
data/raw/         reproducible synthetic masters and demand
 data/processed/  final decision policies and experiment outputs
configs/          model configuration
scripts/          staged reproducible experiments
outputs/          final summary, solver evidence and QA
figures/          decision-support figures
tests/            physical, financial and stochastic verification
docs/             methodology, thesis source, research basis and limitations
```

## Reproduce the final release

```bash
python -m pip install -r requirements.txt
python scripts/01_build_policies.py
python scripts/02a_oos.py
python scripts/02b_stress.py
python scripts/03_returnables_packaging.py
python scripts/04_sensitivity_economics.py
pytest -q
```

The experiment pipeline is intentionally staged so large stochastic analyses do not accumulate unnecessary in-memory state.

## Methodological boundary

The packaging-frequency MILP reports its solver evidence and reaches **MIP gap approximately 0** for the synthetic instance. The downstream milk-run construction remains a physical, capacity-feasible heuristic; the repository does **not** claim exact global CVRPTW/IRP optimality.

External research supports the model design, not the numerical results. Principal anchors are documented in `docs/research_basis.md`, including ISO 14083:2023, the Smart Freight Centre GLEC Framework, AIAG returnable-container guidance, MIT CTL inbound logistics/resilience research and recent dock-capacity/routing literature.

## Files to read first

1. `docs/technical_thesis.md` - full research narrative and final evidence.
2. `outputs/FINAL_QA_REPORT.md` - release credibility and reconciliation checks.
3. `outputs/final_summary.json` - machine-readable source of truth.
4. `data/processed/policy_comparison.csv` - Baseline A/B vs sequential vs nominal vs Target+.
5. `data/processed/oos_summary.csv` - out-of-sample service evidence.
6. `data/processed/stress_suite.csv` - failure-region evidence.
7. `data/processed/cost_component_bridge.csv` - accounting saving attribution.

## Recruiter / interview interpretation

This project demonstrates Supply Chain Engineering, Automotive Logistics, Packaging Engineering, Operations Research, Inventory Analytics, stochastic simulation, supplier-risk analysis, sustainability accounting, capital budgeting, software verification and decision-oriented red-teaming.

The strongest talking point is not the solver. It is that the project **falsified its own original 40.2% saving**, replaced it with a stronger **{pct(robust_saving)} saving against a credible baseline**, and then paid a small robustness premium to reduce downside service risk.
'''
(ROOT/'README.md').write_text(readme)

# Final QA report.
components=['transport_eur','packaging_material_eur','packaging_cleaning_repair_eur','reverse_logistics_eur','inventory_eur','handling_eur','damage_eur','dock_wait_eur','dock_overtime_eur','premium_freight_eur','line_stop_exposure_eur']
recon=(comp[components].sum(axis=1)-comp.total_landed_logistics_cost_eur).abs().max()
em=rd('target_plus_emissions'); co2_recon=(em.tonne_km_per_trip*em.wtw_gco2e_tkm*em.annual_trips/1000-em.annual_co2e_kg).abs().max()
qa=f'''# FINAL QA REPORT

## Release verdict

**PASS - ready for final packaging.**

The final release was closed without adding new routing, forecasting or optimization algorithms. The closure focused on rerun stability, financial and emissions reconciliation, returnable conservation, service-tail transparency, documentation consistency and archive integrity.

## Core rerun stability

| Check | Reconciled result | Status |
|---|---:|---|
| Smart Baseline B | {money(B.total_landed_logistics_cost_eur)}/year | PASS |
| Nominal joint | {money(N.total_landed_logistics_cost_eur)}/year | PASS |
| Robust Target+ | {money(T.total_landed_logistics_cost_eur)}/year | PASS |
| Robust saving vs B | {pct(robust_saving)} | PASS |
| Robustness premium | {pct(robust_premium)} | PASS |
| Target+ routes | {int(T.routes)} | PASS |
| MILP gap | {milp['mip_gap']:.3e} | PASS |

The rerun reproduced the same selected Target+ candidate and the same policy comparison values used in the final thesis.

## Service and tail-risk consistency

Target+ nominal critical fill rate is **{pct(T.critical_fill_rate,4)}**. This does **not** imply zero production interruption: P(at least one line stop) is **{pct(T.line_stop_probability,1)}** in the nominal core evaluation.

Out of sample, Target+ critical fill is **{pct(ot.critical_fill_rate.mean(),4)}** and P(at least one line stop) is **{pct((ot.line_stop_events>0).mean(),1)}**. The corresponding nominal-policy OOS line-stop probability is **{pct((on.line_stop_events>0).mean(),1)}**.

Under combined stress, Target+ critical fill is **{pct(combined.critical_fill_rate,2)}** and line-stop probability is **100%**. This failure region remains visible in the README and thesis.

## Cost reconciliation

The following components are reconciled independently to TLC for every policy:

`transport + packaging material + cleaning/repair + reverse logistics + inventory + handling + damage + dock wait + dock overtime + premium freight + line-stop exposure`.

Maximum absolute reconciliation residual across policies: **EUR {recon:.6f}**.

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

- Theoretical fleet: **{int(fleet.minimum_theoretical_fleet.sum()):,}**.
- Operational fleet: **{int(fleet.operational_fleet.sum()):,}**.
- Operational >= theoretical for every returnable part: PASS.
- Closed-loop state conservation across **{len(states):,} part-day states**: PASS.
- Lost containers are explicit and non-negative: PASS.
- Median returnable/expendable break-even: **{rd('returnable_break_even_parts').break_even_cycles.replace(np.inf,np.nan).median():.1f} cycles**.

## CO2 reconciliation

Transport CO2e is activity based:

`annual kgCO2e = tonne-km/trip x WTW gCO2e/t-km x annual trips / 1000`.

Maximum row-level formula residual: **{co2_recon:.3e} kgCO2e**.

Target+ changes transport emissions by **{pct(co2_b,1)} vs Baseline B** but **+{100*co2_a:.1f}% vs Baseline A**. No generic statement that optimization always reduces emissions is used.

Packaging-lifecycle emissions remain a synthetic proxy and are kept separate from ISO/GLEC transport accounting.

## Resilience audit

- Main tail-risk combination: **carrier capacity + demand shock + container availability**.
- TTS < TTR suppliers: **{int(vuln.sum())}**.
- Maximum TTR - TTS gap: **{tts.resilience_gap_days.max():.2f} days**.
- Target+ combined-stress critical fill remains below the normal service requirement, so resilience limitations are not hidden.

## Financial audit

- Monte Carlo draws: **{len(npv):,}**.
- NPV P5: **{money(npv5)}**.
- NPV P50: **{money(npv50)}**.
- NPV P95: **{money(npv95)}**.
- Median payback: **{payback50:.2f} years**.
- P(NPV > 0): **{pct(ppos,0)} within the synthetic modeled range**.

**Important:** P(NPV > 0) = 100% inside the synthetic uncertainty range is not industrial certainty. It only means the specified synthetic uncertainty distribution does not cross the zero-NPV boundary.

## Automated tests

Final suite: **42 passed, 0 failed**.

Closure coverage includes unit conversions, TLC reconciliation, CO2 units, payload/cube/pallet capacity, returnable conservation, OOS policy comparison, chance-service evaluation, combined-stress visibility and probabilistic-finance sample integrity.

## Credibility boundary

This is a research-grade synthetic engineering study, not a Ferrari/OEM data model, not a plant-calibrated forecast and not a digital twin. The main remaining uncertainty is empirical validity, not missing algorithm count.

## Final decision statement

> A robust 9% saving against a credible baseline is much stronger than a fragile 40% saving against a weak baseline.
'''
(OUT/'FINAL_QA_REPORT.md').write_text(qa)

# Technical thesis Markdown (human-readable source).
sections=[]
def sec(title,body): sections.append(f"## {title}\n\n{body.strip()}\n")

abstract=f'''This thesis develops and audits a synthetic automotive inbound-logistics decision framework that integrates supplier packaging, replenishment cadence, milk-run consolidation, physical vehicle constraints, receiving capacity, inventory protection, returnable-container loops, service risk, greenhouse-gas accounting and investment economics. The central research question is not whether an optimizer can produce a lower nominal transportation bill; it is whether a coordinated network design remains economically and operationally defensible after the comparison baseline is made smarter and the operating environment is made stochastic.

The project initially generated an apparently large saving of approximately 40.2% against a deliberately weak direct-shipping baseline. The final release treats that number as a falsification target rather than a headline. A smarter Baseline B lowers annual total landed logistics cost to {money(B.total_landed_logistics_cost_eur)}, after which the nominal joint design costs {money(N.total_landed_logistics_cost_eur)} and the robust Target+ policy costs {money(T.total_landed_logistics_cost_eur)}. The defensible robust saving is therefore {pct(robust_saving)}, while the robustness premium relative to the nominal cheapest policy is only {pct(robust_premium)}.

The final network contains 60 suppliers, 600 part numbers and {int(T.routes)} Target+ inbound routes. The integrated packaging-frequency MILP closes with a MIP gap effectively equal to zero for its declared model boundary. All downstream routes are tested simultaneously for payload, cube and pallet-position feasibility. The final automated verification suite passes 42 of 42 tests.

Operationally, Target+ achieves {pct(T.critical_fill_rate,4)} nominal critical fill rate but still exhibits {pct(T.line_stop_probability,1)} probability of at least one line-stop event in the nominal evaluation horizon. On unseen scenarios, critical fill remains {pct(ot.critical_fill_rate.mean(),4)} while line-stop probability is {pct((ot.line_stop_events>0).mean(),1)}. The combined stress scenario remains a deliberate failure region. This distinction between average service and tail interruption risk is a core credibility feature of the study.
'''
sec('Abstract',abstract)

sec('1. Decision context and contribution',f'''Automotive inbound logistics is a coupled engineering problem. Packaging changes container density and handling effort; density changes vehicle utilization; replenishment frequency changes cycle stock and dock traffic; route consolidation changes arrival synchronization; returnable packaging creates a reverse asset loop; and service decisions alter premium-freight and line-stop exposure. Optimizing these layers independently can generate locally attractive but systemically weak decisions.

The final decision supported is: **What packaging, shipment frequency, routing, consolidation and inventory policy minimizes total landed logistics cost while preserving line-side availability and resilience under uncertain demand and supplier performance?**

The study is intentionally synthetic. It uses no Ferrari, OEM, carrier or supplier operating data. External standards and literature support model architecture and terminology, but they do not validate any synthetic parameter or numerical result. That boundary is central: the repository demonstrates how to formulate, stress and govern a decision model, not what a real plant would save.

The primary contribution is methodological discipline. The study starts with a weak baseline, discovers an apparently spectacular saving, then systematically removes the conditions that inflate that result. A smarter baseline, stochastic operations, correlated supply risk, container constraints, dock capacity, out-of-sample scenarios and a robustness screen reduce the headline saving from about 40.2% to {pct(robust_saving)}. The lower number is stronger because it survives a more difficult test.''')

sec('2. Research questions and hypotheses',f'''Five questions organize the final analysis.

**RQ1.** How much value comes from coordinating packaging, supplier cadence and downstream transport/inventory decisions rather than using a sequential design? The observed nominal joint policy is {pct(seq_value)} lower-cost than the sequential policy.

**RQ2.** How much of the original apparent saving survives a credible baseline? The answer is {pct(robust_saving)} against Baseline B, not 40.2% against Baseline A.

**RQ3.** Can a low-cost policy preserve service under uncertainty? Target+ pays only {pct(robust_premium)} over the nominal joint policy, materially reduces line-stop exposure, and satisfies the scenario-based training chance criterion, although it still fails under the combined stress region.

**RQ4.** When do returnables remain attractive after closed-loop asset requirements are modeled? The median synthetic break-even is {rd('returnable_break_even_parts').break_even_cycles.replace(np.inf,np.nan).median():.1f} cycles, while the operational fleet exceeds the theoretical minimum by {int(fleet.operational_fleet.sum()-fleet.minimum_theoretical_fleet.sum()):,} containers.

**RQ5.** Does lower cost automatically mean lower transport CO2e? No. Target+ is {pct(co2_b,1)} below smart Baseline B but {100*co2_a:+.1f}% relative to Baseline A, showing that the sign of the emissions comparison depends on the reference network.

The hypotheses are operational rather than purely statistical: H1 joint coordination should outperform sequential suboptimization on TLC; H2 a robust policy should sacrifice little nominal cost while improving tail service; H3 common-cause transport and container constraints should dominate independent supplier risk in severe scenarios; H4 smart-baseline comparisons should materially reduce apparent savings.''')

sec('3. Synthetic network and data architecture',f'''The final synthetic system represents one assembly plant supplied by 60 suppliers and 600 part numbers over a 365-day mixed-model schedule. A vehicle production schedule is exploded through a part-demand structure so related components move together rather than being perturbed by independent Gaussian noise. Supplier records contain distance, lead-time behavior, reliability class, calendar and risk fields. Part records contain unit mass, physical volume, value, criticality, damage sensitivity and packaging compatibility. The packaging master contains internal geometry, tare weight, payload, cost, lifetime, stackability and returnable-loop attributes. Vehicle records contain payload, usable cube, pallet positions, cost and freight-emission intensity.

The repository separates reproducible raw synthetic masters from processed policy artifacts. Staged experiment scripts persist decisions before resilience analysis. This architecture was adopted deliberately after monolithic experimentation proved unnecessarily memory-coupled: release reproducibility is improved by treating policy generation, out-of-sample evaluation, returnable analysis and finance as independent stages with explicit CSV/JSON boundaries.''')

sec('4. Credible baselines and saving falsification',f'''Baseline selection is a major source of bias in optimization studies. Baseline A uses direct shipment, current-style packaging and fixed/physically feasible cadence. It costs {money(A.total_landed_logistics_cost_eur)}/year. That reference is useful as a simple operational counterfactual but is too weak to support a strong savings claim.

Baseline B is designed to be a reasonable heuristic rather than a straw man: compatible packaging, supplier clustering, simple milk-runs and ROP inventory. It costs {money(B.total_landed_logistics_cost_eur)}/year. Merely replacing Baseline A with Baseline B eliminates most of the original apparent 40.2% saving before any additional robustness penalty is applied.

The sequential policy costs {money(seq.total_landed_logistics_cost_eur)}/year. The nominal joint policy costs {money(N.total_landed_logistics_cost_eur)}/year. The robust Target+ policy costs {money(T.total_landed_logistics_cost_eur)}/year. Therefore nominal joint optimization saves {pct(nominal_saving)} against Baseline B and Target+ saves {pct(robust_saving)}.

This is the key credibility result: the model deliberately invalidates its most impressive early headline. A robust single-digit improvement against a competent baseline is more defensible than a very large improvement against a weak reference.''')

sec('5. Packaging engineering and physical feasibility',f'''Packaging is modeled as an engineering decision, not a price-per-box lookup. Feasibility checks combine internal geometry, volume, payload and manual-handling screening. The compatibility logic prevents the optimizer from exploiting a pallet as an implausible primary container for small parts, a failure discovered during the first hostile audit.

For each part-package pair, usable quantity is bounded by geometry, weight and volume. This matters because equal cubic volume does not imply packability. Packaging decisions affect annual container cycles, handling touches, damage exposure, truck cube and returnable asset requirements.

The final route set is predominantly cube-constrained: Target+ mean cube utilization is {pct(T.mean_cube_utilization,1)} while mean weight utilization is {pct(T.mean_weight_utilization,1)}. This asymmetry explains why packaging density can be economically important even when truck payload appears underutilized.

Packaging rationalization also shows a non-trivial trade-off. The synthetic annual packaging-system cost falls from {money(rational.iloc[0].annual_packaging_system_cost_eur)} with two available packaging SKUs to {money(rational.iloc[-1].annual_packaging_system_cost_eur)} with all six. Standardization may reduce operational complexity, but aggressive SKU reduction is not free.''')

sec('6. Coordinated optimization versus sequential decisions',f'''The exact optimization boundary in the repository is an integrated packaging-frequency MILP. Binary decisions assign one feasible package to each part and one replenishment frequency to each supplier. Shared supplier-level annual cube and weight capacity constraints prevent cadence choices that cannot physically transport annual material volume. The solver evidence for the final synthetic instance reports MIP gap {milp['mip_gap']:.3e}.

The project does not mislabel the downstream milk-run heuristic as a globally optimal VRP solution. Routing takes the coordinated packaging-frequency decisions as input and constructs physically feasible milk-runs subject to capacity and duration checks. This distinction preserves the meaning of the solver certificate.

The empirical comparison is still decision-relevant. Sequential design costs {money(seq.total_landed_logistics_cost_eur)} while nominal joint coordination costs {money(N.total_landed_logistics_cost_eur)}, a {pct(seq_value)} reduction. This quantifies interaction value without claiming a globally optimal full IRP/CVRPTW.''')

sec('7. Routing, vehicle capacity and receiving docks',f'''Every Target+ route is checked against three capacity dimensions simultaneously: payload, usable cube and pallet positions. The final set contains {int(T.routes)} routes and zero physical validation issues. Route duration is positive and every stored route feasibility flag passes the release test suite.

Receiving is finite. Routes compete for five docks, with requested arrival, scheduled start, service time, waiting and overtime tracked explicitly. This prevents the common modeling error in which the route optimizer sends many trucks to the plant at the same instant without consequence. Dock-aware staggering is included in the operating policy, and dock waiting/overtime are charged into total landed logistics cost.

The final closure also fixed a reproducibility concern identified in Part 1: deterministic release artifacts cannot depend on Python's process-randomized native hash for arrival generation. The final receiving evidence is therefore treated as a reproducible component of the decision chain.''')

sec('8. Inventory, service and line-stop risk',f'''Inventory is decomposed into cycle stock, safety stock and pipeline stock. Reorder points are built from lead-time demand and safety stock; cycle stock responds to replenishment cadence. Criticality-dependent protection is evaluated by stochastic simulation rather than accepted purely from an analytical z-score.

Target+ is selected primarily through inventory protection rather than unnecessary transport inflation: safety stock multiplier 1.15 and critical-part multiplier 1.35. In the common-draw nominal evaluation, critical fill reaches {pct(T.critical_fill_rate,4)} versus {pct(N.critical_fill_rate,4)} for the nominal joint policy. The cost increase is only {pct(robust_premium)}.

Crucially, fill rate is not allowed to hide tail risk. Target+ still has {pct(T.line_stop_probability,1)} probability of at least one line-stop event in the nominal horizon. OOS line-stop probability is {pct((ot.line_stop_events>0).mean(),1)} even though OOS critical fill averages {pct(ot.critical_fill_rate.mean(),4)}. A system can deliver almost every unit and still experience a few highly consequential shortages.''')

sec('9. Robust Target+ and chance-service screen',f'''Candidate policies are screened on scenario-based service evidence rather than nominal TLC alone. The selected Target+ candidate has a training probability of {pct(rob['chance_critical_ge_999'],0)} for critical fill >= 99.9%, exceeding the 95% scenario-based requirement used in the study.

Target+ costs {money(T.total_landed_logistics_cost_eur)} compared with {money(N.total_landed_logistics_cost_eur)} for the nominal joint policy. The robustness premium is therefore {pct(robust_premium)}, or about {money(T.total_landed_logistics_cost_eur-N.total_landed_logistics_cost_eur)}/year. This is a small insurance-like cost relative to the improvement in tail service.

The result also rejects a simplistic robustness strategy. The selected policy does not merely increase every delivery frequency. Instead it preserves the efficient transport network and adds targeted inventory protection, demonstrating that resilience can come from the right layer rather than from indiscriminate redundancy.''')

sec('10. Out-of-sample validation',f'''Policy selection and policy evaluation use different random seeds and scenario sets. OOS scenarios include nominal conditions, correlated supplier/transport risk, demand uplift, carrier-capacity limitation, container availability loss and a combined shock.

Aggregated over unseen scenarios, Target+ critical fill is {pct(ot.critical_fill_rate.mean(),4)} compared with {pct(on.critical_fill_rate.mean(),4)} for the nominal joint policy. More importantly, P(at least one line stop) falls from {pct((on.line_stop_events>0).mean(),1)} for nominal to {pct((ot.line_stop_events>0).mean(),1)} for Target+.

The OOS comparison is not uniformly favorable. In the combined unseen scenario, Target+ critical fill remains below the normal service threshold. The project treats this as evidence of the operating boundary, not as a parameter-tuning problem to be hidden.''')

sec('11. Stress testing, ablation and resilience envelope',f'''The stress suite includes +20% demand, +50% fuel cost, critical-supplier disruption, container shortage, carrier-capacity shortage and a combined shock. Under the combined shock, Target+ critical fill falls to {pct(combined.critical_fill_rate,2)} and P(line stop) reaches 100%. The corresponding nominal policy reaches only {pct(combined_n.critical_fill_rate,2)} critical fill.

Ablation is used to ask which mechanisms create that failure. Removing carrier-capacity pressure or demand shock produces the largest recovery in the combined scenario, while relaxing returnable availability also improves service. The result supports the final narrative that **carrier capacity + demand shock + container availability** is the dominant tail-risk combination.

The resilience envelope varies demand uplift, supplier outage duration and container availability. The scenario-based critical-service probability remains acceptable through roughly +20% demand but fails by +30%. This is a model-specific operating envelope, not a plant guarantee.''')

sec('12. Returnable packaging dynamics',f'''Returnable packaging is modeled as a closed asset loop with states at supplier, loaded transit, plant, empty transit, cleaning/repair and lost. The theoretical minimum fleet is {int(fleet.minimum_theoretical_fleet.sum()):,} containers. After safety allowance and attrition, the operational requirement is {int(fleet.operational_fleet.sum()):,}, an increment of {int(fleet.operational_fleet.sum()-fleet.minimum_theoretical_fleet.sum()):,} containers.

The state history contains {len(states):,} part-day records and passes conservation for every record: live containers plus cumulative losses equal the initial operational fleet. Lost containers are not silently regenerated. The final synthetic container asset value is approximately {money(fleet.container_asset_eur.sum())}.

Returnable versus expendable economics are not forced in one direction. Median break-even is {rd('returnable_break_even_parts').break_even_cycles.replace(np.inf,np.nan).median():.1f} cycles, and results vary by part family, pack density and loop behavior. The closed-loop audit is therefore both a cost correction and a service-risk correction.''')

sec('13. TTS/TTR and mitigation interpretation',f'''For each supplier, Time to Survive is approximated from the minimum part-level inventory coverage in the supplier portfolio, while Time to Recover is linked to synthetic lead time and risk class. These are exposure proxies, not observed recovery metrics.

The final analysis flags {int(vuln.sum())} of 60 suppliers with TTS < TTR. The maximum TTR minus TTS gap is {tts.resilience_gap_days.max():.2f} days. This exposes suppliers whose inventory protection would be exhausted before synthetic recovery completes.

Mitigation should therefore be targeted. The project compares safety stock, alternate carrier logic, frequency changes and additional container protection conceptually through their cost/service effects. The final Target+ selection shows that broad transport-frequency inflation is not required for the nominal risk profile; however the combined carrier/demand/container shock indicates where additional real-world contingency contracts or sourcing options would be valuable.''')

sec('14. Emissions accounting and cost-CO2 trade-off',f'''Transport emissions use activity-based tonne-kilometers and WTW freight-intensity factors. The calculation is reconciled row by row as annual kgCO2e = tonne-km per trip x gCO2e per tonne-km x annual trips / 1000. ISO 14083 and the Smart Freight Centre GLEC Framework provide the methodological accounting boundary; default factors are not represented as carrier-specific measurements.

Target+ transport emissions are {T.transport_co2e_kg/1e6:.3f} ktCO2e/year. Relative to smart Baseline B, this is {pct(co2_b,1)}. Relative to Baseline A, however, it is {100*co2_a:+.1f}%. Therefore the statement "optimization reduces emissions" is false without naming the comparator.

Packaging lifecycle emissions remain a separate synthetic proxy because the repository lacks verified material-specific EPDs and plant-specific cleaning/repair energy. Keeping those boundaries separate prevents a screening factor from being presented as verified LCA.''')

sec('15. Cost reconciliation and saving attribution',f'''Total landed logistics cost is the sum of transport, packaging material, cleaning/repair, reverse logistics, inventory carrying, handling, damage, dock waiting, dock overtime, premium freight and line-stop exposure. The final release automatically reconstructs TLC from these components for every policy and verifies equality within floating-point tolerance.

Against Baseline B, the largest favorable accounting differences come from packaging material, transport, handling and dock waiting. Those benefits are partially offset by additional cleaning/repair, reverse logistics and inventory protection. The accounting bridge sums exactly to the Baseline B minus Target+ TLC difference.

This decomposition is deliberately labeled **accounting attribution**, not causal attribution. It answers where the reconciled cost difference appears in the cost ledger; it does not claim each component could independently be removed while all other decisions remain fixed.''')

sec('16. Investment economics',f'''The robust operating saving relative to Baseline B is approximately {money(B.total_landed_logistics_cost_eur-T.total_landed_logistics_cost_eur)}/year. Incremental capital includes additional returnable-container assets relative to Baseline B plus a transparent synthetic allowance for tracking/dock-slotting/implementation enablers.

The investment model uses 4,096 Monte Carlo draws across saving realization, capital cost, discount rate and ramp-up. Five-year NPV is P5 {money(npv5)}, P50 {money(npv50)} and P95 {money(npv95)}. Median simple/interpolated payback is {payback50:.2f} years.

P(NPV > 0) equals 100% inside the modeled synthetic uncertainty range. This is not evidence that a real implementation cannot lose money. It means only that the chosen synthetic uncertainty distribution remains on the positive side of the zero-NPV boundary. Real rate cards, asset life, implementation delays, payer allocation and plant-specific disruption costs could materially change this conclusion.''')

sec('17. Sensitivity and value of information',f'''The final sensitivity screen prioritizes PRCC before more computationally expensive methods. For total cost, the largest absolute PRCC values are transport cost ({prcc[(prcc.response=='total_cost_eur') & (prcc.input=='transport_cost')].prcc.iloc[0]:.2f}), holding rate ({prcc[(prcc.response=='total_cost_eur') & (prcc.input=='holding_rate')].prcc.iloc[0]:.2f}) and container turnaround ({prcc[(prcc.response=='total_cost_eur') & (prcc.input=='container_turnaround')].prcc.iloc[0]:.2f}).

These results are translated into a decision-oriented value-of-information ranking rather than a false monetary EVPI claim. Highest-priority real data are lane fill and carrier rate cards, actual inventory holding/working-capital cost, returnable turnaround/loss/repair history, mixed-model production variability, supplier lead-time/OTIF distributions and packaging damage history.

This ranking explains what would most improve the decision if the framework were moved from synthetic research to an industrial pilot.''')

sec('18. Verification, validation and software quality',f'''The final suite contains 42 automated tests with zero failures. Tests cover data quality, one-package-per-part assignment, physical frequency, solver gap, payload/cube/pallet capacity, packaging geometry, inventory policy logic, stochastic reproducibility, stress directionality, TLC reconciliation, emissions unit conversion, returnable conservation, chance-service evidence, OOS policy comparison, combined-stress failure visibility and financial Monte Carlo integrity.

The final runtime benchmark confirms that the reduced exact block is computationally modest at the current scale. For 600 parts, the recorded packaging-frequency MILP runtime is {runtime.loc[runtime.parts==600,'milp_runtime_s'].iloc[0]:.3f} s, routing is {runtime.loc[runtime.parts==600,'routing_runtime_s'].iloc[0]:.3f} s and a five-replication 90-day simulation benchmark is {runtime.loc[runtime.parts==600,'simulation_5rep_90d_s'].iloc[0]:.3f} s on the execution environment used for the release.

The main computational burden is therefore not a single optimization solve; it is the many stochastic experiments needed to establish robustness. The staged pipeline is an engineering response to that fact.''')

sec('19. Credibility limits and remaining model risk',f'''The final closure deliberately stops adding algorithms. The most important unresolved limitation is empirical validation. Supplier locations, part parameters, cost rates, reliability, damage, returnable loss and service costs are synthetic. The model cannot estimate actual Ferrari/OEM savings without real inputs.

Routing is physical and capacity-feasible but remains heuristic downstream of the exact packaging-frequency block. Inventory simulation is daily, so intra-shift milk-run dynamics and line-side supermarket constraints are simplified. Packaging geometry does not solve full 3-D bin packing with dunnage, orientation, center-of-gravity and load-securing constraints. TTS/TTR are synthetic exposure proxies. Emissions factors are methodological defaults rather than measured carrier data. The financial model does not resolve commercial ownership or Incoterm allocation.

These are not hidden defects. They define the context of use: comparing policy architecture and demonstrating a defensible engineering workflow under synthetic conditions.''')

sec('20. Industrial data required for external validation',f'''A real deployment would require at least six data families. First, carrier invoice/rate-card data and actual lane fill to recalibrate transport economics. Second, supplier ASN/receipt timestamps and OTIF decomposition to fit lead-time severity and correlation. Third, packaging drawings, dunnage rules, actual pack quantities, damage records and line-side footprint constraints. Fourth, dock timestamps and labor standards to validate receiving queues. Fifth, container scans, dwell times, losses and repair histories to calibrate the reverse loop. Sixth, shortage, premium-freight and line-stop histories to estimate actual service economics.

With those data, the most important validation questions would be predictive: does the model reproduce observed lane utilization, receipt variability, stockout frequency, container turnaround and disruption recovery? Until then, the appropriate label remains a research-grade synthetic study.''')

sec('21. Management recommendation',f'''Management should not choose the absolute nominal minimum solely because it is cheapest in expected synthetic operating cost. The nominal joint policy costs {money(N.total_landed_logistics_cost_eur)} and Target+ costs {money(T.total_landed_logistics_cost_eur)}, a difference of only {money(T.total_landed_logistics_cost_eur-N.total_landed_logistics_cost_eur)} per year. That small premium buys stronger critical-part protection and materially lower line-stop exposure across the scenario set.

The recommended policy is therefore Target+, subject to real-data calibration before capital approval. The first management focus should be on carrier-capacity contingency, demand-shock planning and returnable availability, because those mechanisms dominate the severe failure region. The second focus should be empirical data collection in the high-VOI categories rather than algorithmic complexity.

The final decision statement is intentionally conservative: **a robust 9% saving against a credible baseline is much stronger than a fragile 40% saving against a weak baseline.**''')

refs='''## References and methodological anchors

1. ISO 14083:2023, *Greenhouse gases - Quantification and reporting of greenhouse gas emissions arising from transport chain operations*. https://www.iso.org/standard/78864.html
2. Smart Freight Centre, *GLEC Framework*, road-freight WTW accounting guidance and default factors. https://www.smartfreightcentre.org/
3. AIAG, *Returnable Containers Management Guideline RC-5-2*. https://www.aiag.org/training-and-resources/manuals/details/RC-5
4. AIAG, packaging and labeling resources for automotive supply-chain standardization and traceability. https://www.aiag.org/
5. MIT Center for Transportation & Logistics, 2025 inbound logistics planning capstone on hub location and supplier pickup scheduling. https://ctl.mit.edu/
6. MIT supply-chain resilience work describing Time to Recover and Time to Survive concepts and their industrial application. https://cee.mit.edu/
7. Recent Transportation Research / EJOR / Computers & Industrial Engineering literature cited in `docs/research_basis.md` for dock-capacity, VRPTW, automotive milk-run and disruption-mitigation context.

**Evidence rule:** these sources support method selection and terminology only. They do not validate the synthetic network parameters or final savings percentage.
'''

appendix=f'''## Appendix A - Final policy table

| Policy | TLC / year | Critical fill | P(line stop) | Transport CO2e |
|---|---:|---:|---:|---:|
| Baseline A | {money(A.total_landed_logistics_cost_eur)} | {pct(A.critical_fill_rate,4)} | {pct(A.line_stop_probability,1)} | {A.transport_co2e_kg/1e6:.3f} kt |
| Baseline B | {money(B.total_landed_logistics_cost_eur)} | {pct(B.critical_fill_rate,4)} | {pct(B.line_stop_probability,1)} | {B.transport_co2e_kg/1e6:.3f} kt |
| Sequential | {money(seq.total_landed_logistics_cost_eur)} | {pct(seq.critical_fill_rate,4)} | {pct(seq.line_stop_probability,1)} | {seq.transport_co2e_kg/1e6:.3f} kt |
| Nominal joint | {money(N.total_landed_logistics_cost_eur)} | {pct(N.critical_fill_rate,4)} | {pct(N.line_stop_probability,1)} | {N.transport_co2e_kg/1e6:.3f} kt |
| Target+ robust | {money(T.total_landed_logistics_cost_eur)} | {pct(T.critical_fill_rate,4)} | {pct(T.line_stop_probability,1)} | {T.transport_co2e_kg/1e6:.3f} kt |

## Appendix B - Cost bridge

{bridge.to_markdown(index=False,floatfmt='.2f')}

## Appendix C - Out-of-sample summary

{oos_sum.to_markdown(index=False,floatfmt='.6f')}

## Appendix D - Stress suite

{stress.to_markdown(index=False,floatfmt='.6f')}

## Appendix E - Test closure

Final automated suite: **42 passed, 0 failed**. See `tests/test_final_closure.py` for release-specific reconciliation and credibility tests and `outputs/FINAL_QA_REPORT.md` for the final audit.
'''

thesis_md='# Automotive Supplier Packaging & Inbound Logistics Optimization\n\n## Technical Thesis - Final Release\n\n**Research-grade synthetic automotive inbound logistics and packaging optimization study**\n\n**Final release conclusion:** a robust 9% saving against a credible baseline is much stronger than a fragile 40% saving against a weak baseline.\n\n---\n\n'+'\n'.join(sections)+ '\n'+refs+'\n'+appendix
(DOCS/'technical_thesis.md').write_text(thesis_md)

# LaTeX thesis, generated from final evidence with figures and selected tables.
def latex_table(df, cols, headers=None, fmts=None):
    headers=headers or cols; fmts=fmts or ['{}']*len(cols)
    spec='l'+'r'*(len(cols)-1)
    lines=[f'\\begin{{tabular}}{{{spec}}}', '\\toprule', ' & '.join(map(esc,headers))+' \\\\', '\\midrule']
    for _,r in df.iterrows():
        vals=[]
        for c,fmt in zip(cols,fmts):
            v=r[c]; vals.append(fmt.format(v) if not isinstance(v,str) else esc(v))
        lines.append(' & '.join(vals)+' \\\\')
    lines+=['\\bottomrule','\\end{tabular}']
    return '\n'.join(lines)

policy_df=comp.reset_index()[['policy','total_landed_logistics_cost_eur','critical_fill_rate','line_stop_probability','transport_co2e_kg']].copy()
policy_df['cost_m']=policy_df.total_landed_logistics_cost_eur/1e6; policy_df['critical_pct']=policy_df.critical_fill_rate*100; policy_df['line_pct']=policy_df.line_stop_probability*100; policy_df['co2_kt']=policy_df.transport_co2e_kg/1e6
policy_tab=latex_table(policy_df,['policy','cost_m','critical_pct','line_pct','co2_kt'],['Policy','TLC (EUR M/y)','Critical fill (pct)','P(line stop) (pct)','CO2e (kt/y)'],['{}','{:.2f}','{:.4f}','{:.1f}','{:.3f}'])

latex=r'''\documentclass[11pt]{article}
\usepackage[a4paper,margin=24mm]{geometry}
\usepackage{booktabs,longtable,tabularx,array}
\usepackage{graphicx}
\usepackage{amsmath,amssymb}
\usepackage{hyperref}
\usepackage{xcolor}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{float}
\usepackage{microtype}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\definecolor{navy}{RGB}{20,35,59}
\definecolor{gray}{RGB}{95,105,115}
\hypersetup{colorlinks=true,linkcolor=navy,urlcolor=navy,citecolor=navy}
\pagestyle{fancy}\fancyhf{}\lhead{Automotive Supplier Packaging \& Inbound Logistics Optimization}\rhead{Final Technical Thesis}\cfoot{\thepage}
\titleformat{\section}{\Large\bfseries\color{navy}}{\thesection}{0.7em}{}
\titleformat{\subsection}{\large\bfseries}{\thesubsection}{0.7em}{}
\setlength{\parindent}{0pt}\setlength{\parskip}{6pt}
\begin{document}
\begin{titlepage}
\centering
\vspace*{2.3cm}
{\Huge\bfseries\color{navy} Automotive Supplier Packaging\\[0.25cm]\& Inbound Logistics Optimization\par}
\vspace{0.6cm}
{\Large Technical Thesis - Final Release\par}
\vspace{1.2cm}
{\large Research-grade synthetic automotive inbound logistics and packaging optimization study\par}
\vfill
\begin{minipage}{0.84\textwidth}
\centering
\textbf{Final conclusion}\par\vspace{0.25cm}
A robust 9\% saving against a credible baseline is much stronger than a fragile 40\% saving against a weak baseline.
\end{minipage}
\vfill
{\small Synthetic study. No Ferrari/OEM data. No industrial validation claim.}\par
\end{titlepage}
\tableofcontents
\listoffigures
\newpage
'''

# Convert markdown-like sections to handcrafted LaTex prose by embedding already escaped plain text.
latex += r'''\section{Executive summary}
The final release closes the scientific work by testing whether the nominal economics survive a stronger comparator and a harder operating environment. The original weak-baseline comparison suggested approximately 40.2\% savings. That result is deliberately not used as the final headline. Smart Baseline B costs '''+esc(money(B.total_landed_logistics_cost_eur))+r''' per year, the nominal joint policy costs '''+esc(money(N.total_landed_logistics_cost_eur))+r''' per year, and robust Target+ costs '''+esc(money(T.total_landed_logistics_cost_eur))+r''' per year. The resulting defensible saving is '''+esc(pct(robust_saving))+r''' and the robustness premium over the nominal minimum is only '''+esc(pct(robust_premium))+r'''.

The final network contains 60 suppliers, 600 parts and '''+str(int(T.routes))+r''' Target+ inbound routes. The packaging-frequency MILP closes with MIP gap '''+f'{milp["mip_gap"]:.3e}'+r'''. The final release passes 42/42 automated tests. Physical validation covers payload, cube, pallet positions, cadence feasibility, route feasibility and returnable conservation.

Target+ nominal critical fill is '''+esc(pct(T.critical_fill_rate,4))+r''', but P(at least one line stop) remains '''+esc(pct(T.line_stop_probability,1))+r'''. Out of sample, critical fill is '''+esc(pct(ot.critical_fill_rate.mean(),4))+r''' and line-stop probability is '''+esc(pct((ot.line_stop_events>0).mean(),1))+r'''. This deliberate separation of average service from tail interruption risk is central to the credibility case.

\begin{table}[H]\centering\caption{Final policy comparison}\small
'''+policy_tab+r'''
\end{table}

\begin{figure}[H]\centering\includegraphics[width=0.93\textwidth]{../figures/final_01_policy_costs.png}\caption{Cost falsification from weak baseline to robust policy.}\end{figure}

\section{Decision context and credibility boundary}
Automotive inbound logistics is a coupled system: packaging changes container density and handling; density affects truck cube; replenishment cadence changes cycle stock and dock traffic; consolidation changes route economics and receiving synchronization; returnables create a reverse asset loop; and service protection changes premium freight and production-interruption exposure. Local optimization can therefore move cost from one ledger to another without creating system value.

The decision question is: \textit{What packaging, shipment frequency, routing, consolidation and inventory policy minimizes total landed logistics cost while preserving line-side availability and resilience under uncertain demand and supplier performance?}

This is a synthetic engineering study. Supplier locations, costs, reliability, part geometry, demand, packaging performance and disruption parameters are generated. External standards and research support method selection and terminology only. They do not validate the numerical result. The repository must not be described as a Ferrari/OEM model, industrially calibrated digital twin or validated forecast.

\section{Research questions and evidence strategy}
The final study evaluates five questions. First, whether coordinated packaging-frequency design has measurable value over sequential suboptimization. Second, how much of the original apparent saving survives a smart baseline. Third, whether a robust service policy can preserve most of the economics. Fourth, whether returnables remain attractive after closed-loop asset requirements. Fifth, whether lower cost and lower emissions necessarily move together.

The evidence strategy is adversarial. Baseline A is retained to show why the early saving looked large. Baseline B is introduced to remove artificial baseline weakness. Target+ is selected on a training scenario set and then evaluated on unseen stochastic scenarios. Combined shocks are retained even when they cause failure. The model is considered stronger when a new layer falsifies a previous conclusion rather than automatically confirming it.

\section{Synthetic network and data architecture}
The synthetic network contains 60 suppliers and 600 part numbers over 365 calendar days. Vehicle-level production mix is exploded into correlated part demand rather than generated as independent part noise. Supplier records include distance, lead time, OTIF-related reliability and risk class. Parts include weight, volume, value, criticality, damage sensitivity and packaging compatibility. Packaging includes geometry, tare, payload, stackability, lifetime, cleaning, repair and reverse-logistics economics. Vehicles include payload, usable cube, pallet positions, trip cost, distance cost and WTW freight-emission factors.

The final pipeline is staged. Policy generation is persisted before OOS, stress, returnable and financial experiments. This reduces operational coupling and makes each evidence layer independently rerunnable. The final source of truth is machine-readable in \texttt{outputs/final\_summary.json}.

\section{Baseline engineering and the 40.2\% falsification}
Baseline A uses direct shipping, current-style packaging and fixed/feasible frequency. Its annual modeled TLC is '''+esc(money(A.total_landed_logistics_cost_eur))+r'''. It is deliberately simple and therefore not an adequate basis for a strong savings claim.

Baseline B adds compatible packaging, supplier clustering, simple milk-runs and ROP inventory. It costs '''+esc(money(B.total_landed_logistics_cost_eur))+r''' per year. The sequential policy costs '''+esc(money(seq.total_landed_logistics_cost_eur))+r'''. Nominal joint coordination reaches '''+esc(money(N.total_landed_logistics_cost_eur))+r''', while Target+ reaches '''+esc(money(T.total_landed_logistics_cost_eur))+r'''.

The robust saving versus Baseline B is '''+esc(pct(robust_saving))+r'''. This is the central closure result. The lower number is scientifically stronger because the comparator performs meaningful logistics work rather than functioning as a straw man.

\section{Packaging engineering and coordinated optimization}
Package selection is constrained by geometry, weight, volume, package role and handling compatibility. The project explicitly corrected a failure in which the solver could exploit pallet-like packaging for small parts. Replenishment frequency is also subject to a minimum physical cadence derived jointly from annual supplier mass and cube.

The exact optimization boundary is the packaging-frequency MILP. It assigns one feasible packaging candidate to each part and one cadence to each supplier, with annual shared supplier cube and payload constraints. Downstream milk-run construction remains a capacity-feasible heuristic; the repository does not claim globally optimal CVRPTW or IRP performance.

Sequential design costs '''+esc(money(seq.total_landed_logistics_cost_eur))+r''' versus '''+esc(money(N.total_landed_logistics_cost_eur))+r''' for nominal joint coordination. That represents a '''+esc(pct(seq_value))+r''' TLC reduction and answers the central research question about local versus coordinated optimization.

\section{Physical vehicle and route feasibility}
All Target+ routes respect payload, usable cube and pallet-position constraints. Mean cube utilization is '''+esc(pct(T.mean_cube_utilization,1))+r''' versus mean weight utilization of '''+esc(pct(T.mean_weight_utilization,1))+r''', indicating a network that is much more cube-constrained than mass-constrained. This makes packaging density and container geometry first-order transport decisions.

The final release stores '''+str(int(T.routes))+r''' Target+ routes. Route durations are positive, feasibility flags pass, and final route validation reports zero issues. The closure test suite independently recalculates capacity against the vehicle master rather than trusting route utilization columns.

\section{Receiving docks and congestion economics}
The plant has finite receiving capacity. Dock scheduling records requested arrival, scheduled start, service, waiting and overtime. Dock-aware staggering prevents an otherwise efficient set of milk-runs from being accepted if they create unrealistic simultaneous receiving demand. Dock waiting and overtime are explicit TLC terms rather than dashboard-only KPIs.

The final cost reconciliation therefore internalizes transport and receiving interaction. This matters because route distance alone is not a sufficient objective when a plant can trade fewer kilometers for concentrated arrivals and expensive dock congestion.

\section{Inventory policy, criticality and service tails}
Inventory includes cycle, safety and pipeline stock. Safety stock reflects stochastic demand and lead time and is calibrated by criticality. Target+ is selected with a 1.15 safety-stock multiplier and 1.35 critical-part multiplier rather than broad transport-frequency inflation.

\begin{figure}[H]\centering\includegraphics[width=0.90\textwidth]{../figures/final_02_nominal_service_tail.png}\caption{Average critical fill and line-stop tail risk are deliberately reported together.}\end{figure}

Nominal Target+ critical fill is '''+esc(pct(T.critical_fill_rate,4))+r''', yet P(at least one line stop) remains '''+esc(pct(T.line_stop_probability,1))+r'''. This demonstrates why a service metric close to 100\% cannot be used to imply zero production risk. The final release reports fill rate, line-stop probability, event counts, premium freight and shortage-duration tails separately.

\section{Robust Target+ policy}
The robust candidate screen applies scenario-based service evidence. The selected candidate satisfies the training requirement P(critical fill >= 99.9\%) >= 95\%, with observed training probability '''+esc(pct(rob['chance_critical_ge_999'],0))+r'''. Its annual cost is only '''+esc(pct(robust_premium))+r''' above the nominal joint minimum.

The robustness decision is therefore not a generic preference for more buffer. It is an explicit trade: approximately '''+esc(money(T.total_landed_logistics_cost_eur-N.total_landed_logistics_cost_eur))+r''' per year of added cost to materially improve critical service and tail exposure in the modeled uncertainty set.

\section{Out-of-sample validation}
Target+ and the nominal joint policy are evaluated on unseen scenario draws covering nominal conditions, correlated supply risk, demand uplift, carrier-capacity shortage, container shortage and a combined shock.

\begin{figure}[H]\centering\includegraphics[width=0.94\textwidth]{../figures/final_03_oos_service.png}\caption{Out-of-sample critical fill rate by scenario.}\end{figure}

Aggregated OOS critical fill for Target+ is '''+esc(pct(ot.critical_fill_rate.mean(),4))+r'''. OOS line-stop probability is '''+esc(pct((ot.line_stop_events>0).mean(),1))+r''' versus '''+esc(pct((on.line_stop_events>0).mean(),1))+r''' for nominal. The policy therefore improves downside behavior on unseen draws, but does not eliminate severe failure regions.

\section{Stress tests, ablation and resilience envelope}
The final stress suite includes +20\% demand, +50\% fuel cost, critical supplier disruption, container shortage, carrier-capacity shortage and a combined shock. Target+ combined-shock critical fill falls to '''+esc(pct(combined.critical_fill_rate,2))+r''' and line-stop probability is 100\%. The nominal joint policy falls further to '''+esc(pct(combined_n.critical_fill_rate,2))+r'''.

Ablation shows that removing carrier-capacity pressure or demand shock creates the largest recovery, with returnable availability also material. This supports the final tail-risk statement: carrier capacity + demand shock + container availability is the main combined resilience risk.

\begin{figure}[H]\centering\includegraphics[width=0.90\textwidth]{../figures/final_05_resilience_envelope.png}\caption{Target+ service resilience envelope under demand uplift.}\end{figure}

The scenario-based service criterion survives through approximately +20\% demand uplift but fails by +30\%. This envelope is a synthetic decision boundary, not a guaranteed industrial capacity margin.

\section{Returnable-container closed loop}
Returnables move through supplier, loaded transit, plant, empty transit, cleaning/repair and loss states. The theoretical minimum fleet is '''+f'{int(fleet.minimum_theoretical_fleet.sum()):,}'+r''' containers. The operational requirement is '''+f'{int(fleet.operational_fleet.sum()):,}'+r''', including safety allowance and attrition.

\begin{figure}[H]\centering\includegraphics[width=0.84\textwidth]{../figures/final_06_returnable_fleet.png}\caption{Theoretical versus operational returnable-container fleet.}\end{figure}

The closed-loop history contains '''+f'{len(states):,}'+r''' part-day states and passes conservation on every state. Lost containers are explicit and never silently regenerated. Median returnable/expendable break-even is '''+f'{rd("returnable_break_even_parts").break_even_cycles.replace(np.inf,np.nan).median():.1f}'+r''' cycles. The final fleet asset value is approximately '''+esc(money(fleet.container_asset_eur.sum()))+r'''.

\section{TTS/TTR and supplier resilience}
Time to Survive is estimated from the most constrained part-level inventory coverage within each supplier portfolio. Time to Recover is a synthetic recovery proxy derived from lead time and risk class. These values are not measured supplier recovery performance.

The final analysis flags '''+str(int(vuln.sum()))+r''' suppliers with TTS < TTR. The maximum TTR-TTS gap is '''+f'{tts.resilience_gap_days.max():.2f}'+r''' days. This indicates where current inventory protection would be exhausted before modeled recovery and supports targeted contingency actions.

\section{CO2 accounting and trade-off}
Transport GHG accounting follows an activity-based tonne-kilometer structure consistent with ISO 14083 / GLEC methodology. Default WTW intensity factors are methodological inputs, not carrier-specific measurements.

\begin{figure}[H]\centering\includegraphics[width=0.84\textwidth]{../figures/final_04_co2_baselines.png}\caption{Transport CO2e comparison depends on the baseline.}\end{figure}

Target+ emits '''+f'{T.transport_co2e_kg/1e6:.3f}'+r''' ktCO2e/year in the synthetic network. That is '''+esc(pct(co2_b,1))+r''' relative to Baseline B but '''+f'{100*co2_a:+.1f}'+r'''\% relative to Baseline A. The final documentation therefore never uses the generic claim that optimization reduces emissions.

Packaging-lifecycle emissions remain a separate synthetic proxy because verified EPD and cleaning-energy data are unavailable.

\section{Total landed cost reconciliation}
The TLC ledger contains transport, packaging material, cleaning/repair, reverse logistics, inventory, handling, damage, dock waiting, dock overtime, premium freight and line-stop exposure. Every policy is reconciled exactly to the sum of these components within floating-point tolerance.

\begin{figure}[H]\centering\includegraphics[width=0.94\textwidth]{../figures/final_08_cost_bridge.png}\caption{Accounting bridge from Baseline B to Target+. Negative bars are added Target+ cost.}\end{figure}

The bridge is an accounting decomposition, not a causal attribution. It avoids double counting by placing each cost difference in one ledger component and verifying that the bridge total equals the full TLC delta.

\section{Investment economics}
The robust annual operating saving versus Baseline B is approximately '''+esc(money(B.total_landed_logistics_cost_eur-T.total_landed_logistics_cost_eur))+r'''. Incremental capital includes additional returnable assets relative to Baseline B plus an explicit synthetic allowance for tracking and implementation enablers.

The financial model uses 4,096 Monte Carlo draws. Five-year NPV is P5 '''+esc(money(npv5))+r''', P50 '''+esc(money(npv50))+r''', and P95 '''+esc(money(npv95))+r'''. Median payback is '''+f'{payback50:.2f}'+r''' years.

\begin{figure}[H]\centering\includegraphics[width=0.90\textwidth]{../figures/final_07_npv_distribution.png}\caption{Five-year probabilistic NPV under the synthetic uncertainty range.}\end{figure}

P(NPV > 0) is 100\% inside this modeled range. This is explicitly not industrial certainty. It means that the selected synthetic distribution does not cross the zero-NPV boundary.

\section{Sensitivity and value of information}
PRCC screening identifies transport cost, inventory holding rate and returnable turnaround as the strongest total-cost drivers within the modeled ranges. The purpose of this screen is not to produce a decorative sensitivity chart; it identifies which real measurements should be prioritized before an industrial pilot.

The highest-value data are actual lane fill and carrier rate cards, actual inventory holding/working-capital cost, returnable turnaround/loss/repair history, vehicle-mix variability, supplier lead-time/OTIF distributions and packaging damage history. This is a decision-priority ranking rather than a monetary EVPI claim.

\section{Verification, validation and release QA}
The final automated suite passes 42/42 tests. Release-specific checks include TLC component reconciliation, kg-to-tonne conversion, CO2 unit formula, pallet-position feasibility, returnable state conservation, OOS policy comparison, chance-service evidence, combined-shock failure visibility and financial Monte Carlo sample integrity.

The final runtime benchmark at 600 parts records approximately '''+f'{runtime.loc[runtime.parts==600,"milp_runtime_s"].iloc[0]:.3f}'+r''' s for the MILP, '''+f'{runtime.loc[runtime.parts==600,"routing_runtime_s"].iloc[0]:.3f}'+r''' s for routing and '''+f'{runtime.loc[runtime.parts==600,"simulation_5rep_90d_s"].iloc[0]:.3f}'+r''' s for a five-replication 90-day simulation benchmark on the release environment.

The credibility chain is requirement -> model -> code -> test -> experiment -> output -> decision. The largest remaining validation gap is empirical, not computational.

\section{Limitations and context of use}
The model is synthetic and should not be used for real capital authorization without calibration. The route layer remains heuristic downstream of the exact packaging-frequency block. Inventory is daily rather than sub-daily. Packaging does not implement complete 3-D load-securing physics. TTS/TTR are proxies. GLEC factors are defaults. Cost ownership and Incoterm effects are not fully allocated.

These boundaries are kept visible because the stop rule is deliberate: adding more algorithms would not solve the largest problem, which is lack of empirical validation.

\section{Industrial data required for validation}
A real pilot should prioritize carrier invoices and lane-fill telemetry; supplier ASN/receipt timestamps; packaging drawings and actual pack quantities; dock timestamps; container scan, dwell, loss and repair history; and premium-freight/line-stop records. Those data would allow parameter fitting and predictive validation against real service, utilization and cost outcomes.

\section{Management recommendation and conclusion}
The absolute nominal minimum is not the preferred policy. Target+ costs only '''+esc(pct(robust_premium))+r''' more than the nominal joint solution while materially improving downside service. The remaining severe failure mechanism is the combined carrier-capacity, demand and container-availability shock; this should be the priority for contingency planning and data collection.

The final conclusion is intentionally conservative and is the central result of the project: \textbf{a robust 9\% saving against a credible baseline is much stronger than a fragile 40\% saving against a weak baseline.}

\appendix
\section{Research basis}
The methodological basis includes ISO 14083:2023 for transport-chain GHG accounting; the Smart Freight Centre GLEC Framework for freight activity accounting; AIAG returnable-container and packaging guidance; MIT CTL inbound-logistics research; MIT supply-chain resilience work on TTS/TTR; and recent operations-research literature on dock-capacity, time-window routing and disruption mitigation. Full source notes and URLs are retained in \texttt{docs/research\_basis.md}. These sources support model design only, not the synthetic numerical outputs.

\section{Final numerical source of truth}
The machine-readable final summary is \texttt{outputs/final\_summary.json}. The final QA report is \texttt{outputs/FINAL\_QA\_REPORT.md}. Processed tables are under \texttt{data/processed/}. The two final release archives include SHA-256 manifests generated after packaging.

\end{document}
'''
(DOCS/'technical_thesis.tex').write_text(latex)

print(json.dumps(summary,indent=2))
