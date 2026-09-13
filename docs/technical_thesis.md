# Automotive Supplier Packaging & Inbound Logistics Optimization

## Technical Thesis - Final Release

**Research-grade synthetic automotive inbound logistics and packaging optimization study**

**Final release conclusion:** a robust 9% saving against a credible baseline is much stronger than a fragile 40% saving against a weak baseline.

---

## Abstract

This thesis develops and audits a synthetic automotive inbound-logistics decision framework that integrates supplier packaging, replenishment cadence, milk-run consolidation, physical vehicle constraints, receiving capacity, inventory protection, returnable-container loops, service risk, greenhouse-gas accounting and investment economics. The central research question is not whether an optimizer can produce a lower nominal transportation bill; it is whether a coordinated network design remains economically and operationally defensible after the comparison baseline is made smarter and the operating environment is made stochastic.

The project initially generated an apparently large saving of approximately 40.2% against a deliberately weak direct-shipping baseline. The final release treats that number as a falsification target rather than a headline. A smarter Baseline B lowers annual total landed logistics cost to EUR 52.92M, after which the nominal joint design costs EUR 47.86M and the robust Target+ policy costs EUR 47.98M. The defensible robust saving is therefore 9.33%, while the robustness premium relative to the nominal cheapest policy is only 0.26%.

The final network contains 60 suppliers, 600 part numbers and 57 Target+ inbound routes. The integrated packaging-frequency MILP closes with a MIP gap effectively equal to zero for its declared model boundary. All downstream routes are tested simultaneously for payload, cube and pallet-position feasibility. The final automated verification suite passes 42 of 42 tests.

Operationally, Target+ achieves 99.9991% nominal critical fill rate but still exhibits 6.7% probability of at least one line-stop event in the nominal evaluation horizon. On unseen scenarios, critical fill remains 99.9046% while line-stop probability is 48.0%. The combined stress scenario remains a deliberate failure region. This distinction between average service and tail interruption risk is a core credibility feature of the study.

## 1. Decision context and contribution

Automotive inbound logistics is a coupled engineering problem. Packaging changes container density and handling effort; density changes vehicle utilization; replenishment frequency changes cycle stock and dock traffic; route consolidation changes arrival synchronization; returnable packaging creates a reverse asset loop; and service decisions alter premium-freight and line-stop exposure. Optimizing these layers independently can generate locally attractive but systemically weak decisions.

The final decision supported is: **What packaging, shipment frequency, routing, consolidation and inventory policy minimizes total landed logistics cost while preserving line-side availability and resilience under uncertain demand and supplier performance?**

The study is intentionally synthetic. It uses no Ferrari, OEM, carrier or supplier operating data. External standards and literature support model architecture and terminology, but they do not validate any synthetic parameter or numerical result. That boundary is central: the repository demonstrates how to formulate, stress and govern a decision model, not what a real plant would save.

The primary contribution is methodological discipline. The study starts with a weak baseline, discovers an apparently spectacular saving, then systematically removes the conditions that inflate that result. A smarter baseline, stochastic operations, correlated supply risk, container constraints, dock capacity, out-of-sample scenarios and a robustness screen reduce the headline saving from about 40.2% to 9.33%. The lower number is stronger because it survives a more difficult test.

## 2. Research questions and hypotheses

Five questions organize the final analysis.

**RQ1.** How much value comes from coordinating packaging, supplier cadence and downstream transport/inventory decisions rather than using a sequential design? The observed nominal joint policy is 6.62% lower-cost than the sequential policy.

**RQ2.** How much of the original apparent saving survives a credible baseline? The answer is 9.33% against Baseline B, not 40.2% against Baseline A.

**RQ3.** Can a low-cost policy preserve service under uncertainty? Target+ pays only 0.26% over the nominal joint policy, materially reduces line-stop exposure, and satisfies the scenario-based training chance criterion, although it still fails under the combined stress region.

**RQ4.** When do returnables remain attractive after closed-loop asset requirements are modeled? The median synthetic break-even is 69.4 cycles, while the operational fleet exceeds the theoretical minimum by 20,384 containers.

**RQ5.** Does lower cost automatically mean lower transport CO2e? No. Target+ is -13.8% below smart Baseline B but +0.3% relative to Baseline A, showing that the sign of the emissions comparison depends on the reference network.

The hypotheses are operational rather than purely statistical: H1 joint coordination should outperform sequential suboptimization on TLC; H2 a robust policy should sacrifice little nominal cost while improving tail service; H3 common-cause transport and container constraints should dominate independent supplier risk in severe scenarios; H4 smart-baseline comparisons should materially reduce apparent savings.

## 3. Synthetic network and data architecture

The final synthetic system represents one assembly plant supplied by 60 suppliers and 600 part numbers over a 365-day mixed-model schedule. A vehicle production schedule is exploded through a part-demand structure so related components move together rather than being perturbed by independent Gaussian noise. Supplier records contain distance, lead-time behavior, reliability class, calendar and risk fields. Part records contain unit mass, physical volume, value, criticality, damage sensitivity and packaging compatibility. The packaging master contains internal geometry, tare weight, payload, cost, lifetime, stackability and returnable-loop attributes. Vehicle records contain payload, usable cube, pallet positions, cost and freight-emission intensity.

The repository separates reproducible raw synthetic masters from processed policy artifacts. Staged experiment scripts persist decisions before resilience analysis. This architecture was adopted deliberately after monolithic experimentation proved unnecessarily memory-coupled: release reproducibility is improved by treating policy generation, out-of-sample evaluation, returnable analysis and finance as independent stages with explicit CSV/JSON boundaries.

## 4. Credible baselines and saving falsification

Baseline selection is a major source of bias in optimization studies. Baseline A uses direct shipment, current-style packaging and fixed/physically feasible cadence. It costs EUR 81.82M/year. That reference is useful as a simple operational counterfactual but is too weak to support a strong savings claim.

Baseline B is designed to be a reasonable heuristic rather than a straw man: compatible packaging, supplier clustering, simple milk-runs and ROP inventory. It costs EUR 52.92M/year. Merely replacing Baseline A with Baseline B eliminates most of the original apparent 40.2% saving before any additional robustness penalty is applied.

The sequential policy costs EUR 51.25M/year. The nominal joint policy costs EUR 47.86M/year. The robust Target+ policy costs EUR 47.98M/year. Therefore nominal joint optimization saves 9.57% against Baseline B and Target+ saves 9.33%.

This is the key credibility result: the model deliberately invalidates its most impressive early headline. A robust single-digit improvement against a competent baseline is more defensible than a very large improvement against a weak reference.

## 5. Packaging engineering and physical feasibility

Packaging is modeled as an engineering decision, not a price-per-box lookup. Feasibility checks combine internal geometry, volume, payload and manual-handling screening. The compatibility logic prevents the optimizer from exploiting a pallet as an implausible primary container for small parts, a failure discovered during the first hostile audit.

For each part-package pair, usable quantity is bounded by geometry, weight and volume. This matters because equal cubic volume does not imply packability. Packaging decisions affect annual container cycles, handling touches, damage exposure, truck cube and returnable asset requirements.

The final route set is predominantly cube-constrained: Target+ mean cube utilization is 74.7% while mean weight utilization is 26.2%. This asymmetry explains why packaging density can be economically important even when truck payload appears underutilized.

Packaging rationalization also shows a non-trivial trade-off. The synthetic annual packaging-system cost falls from EUR 122.01M with two available packaging SKUs to EUR 86.44M with all six. Standardization may reduce operational complexity, but aggressive SKU reduction is not free.

## 6. Coordinated optimization versus sequential decisions

The exact optimization boundary in the repository is an integrated packaging-frequency MILP. Binary decisions assign one feasible package to each part and one replenishment frequency to each supplier. Shared supplier-level annual cube and weight capacity constraints prevent cadence choices that cannot physically transport annual material volume. The solver evidence for the final synthetic instance reports MIP gap 1.019e-15.

The project does not mislabel the downstream milk-run heuristic as a globally optimal VRP solution. Routing takes the coordinated packaging-frequency decisions as input and constructs physically feasible milk-runs subject to capacity and duration checks. This distinction preserves the meaning of the solver certificate.

The empirical comparison is still decision-relevant. Sequential design costs EUR 51.25M while nominal joint coordination costs EUR 47.86M, a 6.62% reduction. This quantifies interaction value without claiming a globally optimal full IRP/CVRPTW.

## 7. Routing, vehicle capacity and receiving docks

Every Target+ route is checked against three capacity dimensions simultaneously: payload, usable cube and pallet positions. The final set contains 57 routes and zero physical validation issues. Route duration is positive and every stored route feasibility flag passes the release test suite.

Receiving is finite. Routes compete for five docks, with requested arrival, scheduled start, service time, waiting and overtime tracked explicitly. This prevents the common modeling error in which the route optimizer sends many trucks to the plant at the same instant without consequence. Dock-aware staggering is included in the operating policy, and dock waiting/overtime are charged into total landed logistics cost.

The final closure also fixed a reproducibility concern identified in Part 1: deterministic release artifacts cannot depend on Python's process-randomized native hash for arrival generation. The final receiving evidence is therefore treated as a reproducible component of the decision chain.

## 8. Inventory, service and line-stop risk

Inventory is decomposed into cycle stock, safety stock and pipeline stock. Reorder points are built from lead-time demand and safety stock; cycle stock responds to replenishment cadence. Criticality-dependent protection is evaluated by stochastic simulation rather than accepted purely from an analytical z-score.

Target+ is selected primarily through inventory protection rather than unnecessary transport inflation: safety stock multiplier 1.15 and critical-part multiplier 1.35. In the common-draw nominal evaluation, critical fill reaches 99.9991% versus 99.9912% for the nominal joint policy. The cost increase is only 0.26%.

Crucially, fill rate is not allowed to hide tail risk. Target+ still has 6.7% probability of at least one line-stop event in the nominal horizon. OOS line-stop probability is 48.0% even though OOS critical fill averages 99.9046%. A system can deliver almost every unit and still experience a few highly consequential shortages.

## 9. Robust Target+ and chance-service screen

Candidate policies are screened on scenario-based service evidence rather than nominal TLC alone. The selected Target+ candidate has a training probability of 100% for critical fill >= 99.9%, exceeding the 95% scenario-based requirement used in the study.

Target+ costs EUR 47.98M compared with EUR 47.86M for the nominal joint policy. The robustness premium is therefore 0.26%, or about EUR 126.3k/year. This is a small insurance-like cost relative to the improvement in tail service.

The result also rejects a simplistic robustness strategy. The selected policy does not merely increase every delivery frequency. Instead it preserves the efficient transport network and adds targeted inventory protection, demonstrating that resilience can come from the right layer rather than from indiscriminate redundancy.

## 10. Out-of-sample validation

Policy selection and policy evaluation use different random seeds and scenario sets. OOS scenarios include nominal conditions, correlated supplier/transport risk, demand uplift, carrier-capacity limitation, container availability loss and a combined shock.

Aggregated over unseen scenarios, Target+ critical fill is 99.9046% compared with 99.7912% for the nominal joint policy. More importantly, P(at least one line stop) falls from 87.3% for nominal to 48.0% for Target+.

The OOS comparison is not uniformly favorable. In the combined unseen scenario, Target+ critical fill remains below the normal service threshold. The project treats this as evidence of the operating boundary, not as a parameter-tuning problem to be hidden.

## 11. Stress testing, ablation and resilience envelope

The stress suite includes +20% demand, +50% fuel cost, critical-supplier disruption, container shortage, carrier-capacity shortage and a combined shock. Under the combined shock, Target+ critical fill falls to 97.34% and P(line stop) reaches 100%. The corresponding nominal policy reaches only 96.73% critical fill.

Ablation is used to ask which mechanisms create that failure. Removing carrier-capacity pressure or demand shock produces the largest recovery in the combined scenario, while relaxing returnable availability also improves service. The result supports the final narrative that **carrier capacity + demand shock + container availability** is the dominant tail-risk combination.

The resilience envelope varies demand uplift, supplier outage duration and container availability. The scenario-based critical-service probability remains acceptable through roughly +20% demand but fails by +30%. This is a model-specific operating envelope, not a plant guarantee.

## 12. Returnable packaging dynamics

Returnable packaging is modeled as a closed asset loop with states at supplier, loaded transit, plant, empty transit, cleaning/repair and lost. The theoretical minimum fleet is 129,888 containers. After safety allowance and attrition, the operational requirement is 150,272, an increment of 20,384 containers.

The state history contains 95,220 part-day records and passes conservation for every record: live containers plus cumulative losses equal the initial operational fleet. Lost containers are not silently regenerated. The final synthetic container asset value is approximately EUR 33.03M.

Returnable versus expendable economics are not forced in one direction. Median break-even is 69.4 cycles, and results vary by part family, pack density and loop behavior. The closed-loop audit is therefore both a cost correction and a service-risk correction.

## 13. TTS/TTR and mitigation interpretation

For each supplier, Time to Survive is approximated from the minimum part-level inventory coverage in the supplier portfolio, while Time to Recover is linked to synthetic lead time and risk class. These are exposure proxies, not observed recovery metrics.

The final analysis flags 28 of 60 suppliers with TTS < TTR. The maximum TTR minus TTS gap is 5.73 days. This exposes suppliers whose inventory protection would be exhausted before synthetic recovery completes.

Mitigation should therefore be targeted. The project compares safety stock, alternate carrier logic, frequency changes and additional container protection conceptually through their cost/service effects. The final Target+ selection shows that broad transport-frequency inflation is not required for the nominal risk profile; however the combined carrier/demand/container shock indicates where additional real-world contingency contracts or sourcing options would be valuable.

## 14. Emissions accounting and cost-CO2 trade-off

Transport emissions use activity-based tonne-kilometers and WTW freight-intensity factors. The calculation is reconciled row by row as annual kgCO2e = tonne-km per trip x gCO2e per tonne-km x annual trips / 1000. ISO 14083 and the Smart Freight Centre GLEC Framework provide the methodological accounting boundary; default factors are not represented as carrier-specific measurements.

Target+ transport emissions are 3.347 ktCO2e/year. Relative to smart Baseline B, this is -13.8%. Relative to Baseline A, however, it is +0.3%. Therefore the statement "optimization reduces emissions" is false without naming the comparator.

Packaging lifecycle emissions remain a separate synthetic proxy because the repository lacks verified material-specific EPDs and plant-specific cleaning/repair energy. Keeping those boundaries separate prevents a screening factor from being presented as verified LCA.

## 15. Cost reconciliation and saving attribution

Total landed logistics cost is the sum of transport, packaging material, cleaning/repair, reverse logistics, inventory carrying, handling, damage, dock waiting, dock overtime, premium freight and line-stop exposure. The final release automatically reconstructs TLC from these components for every policy and verifies equality within floating-point tolerance.

Against Baseline B, the largest favorable accounting differences come from packaging material, transport, handling and dock waiting. Those benefits are partially offset by additional cleaning/repair, reverse logistics and inventory protection. The accounting bridge sums exactly to the Baseline B minus Target+ TLC difference.

This decomposition is deliberately labeled **accounting attribution**, not causal attribution. It answers where the reconciled cost difference appears in the cost ledger; it does not claim each component could independently be removed while all other decisions remain fixed.

## 16. Investment economics

The robust operating saving relative to Baseline B is approximately EUR 4.94M/year. Incremental capital includes additional returnable-container assets relative to Baseline B plus a transparent synthetic allowance for tracking/dock-slotting/implementation enablers.

The investment model uses 4,096 Monte Carlo draws across saving realization, capital cost, discount rate and ramp-up. Five-year NPV is P5 EUR 3.15M, P50 EUR 6.39M and P95 EUR 9.49M. Median simple/interpolated payback is 2.39 years.

P(NPV > 0) equals 100% inside the modeled synthetic uncertainty range. This is not evidence that a real implementation cannot lose money. It means only that the chosen synthetic uncertainty distribution remains on the positive side of the zero-NPV boundary. Real rate cards, asset life, implementation delays, payer allocation and plant-specific disruption costs could materially change this conclusion.

## 17. Sensitivity and value of information

The final sensitivity screen prioritizes PRCC before more computationally expensive methods. For total cost, the largest absolute PRCC values are transport cost (0.93), holding rate (0.92) and container turnaround (0.85).

These results are translated into a decision-oriented value-of-information ranking rather than a false monetary EVPI claim. Highest-priority real data are lane fill and carrier rate cards, actual inventory holding/working-capital cost, returnable turnaround/loss/repair history, mixed-model production variability, supplier lead-time/OTIF distributions and packaging damage history.

This ranking explains what would most improve the decision if the framework were moved from synthetic research to an industrial pilot.

## 18. Verification, validation and software quality

The final suite contains 42 automated tests with zero failures. Tests cover data quality, one-package-per-part assignment, physical frequency, solver gap, payload/cube/pallet capacity, packaging geometry, inventory policy logic, stochastic reproducibility, stress directionality, TLC reconciliation, emissions unit conversion, returnable conservation, chance-service evidence, OOS policy comparison, combined-stress failure visibility and financial Monte Carlo integrity.

The final runtime benchmark confirms that the reduced exact block is computationally modest at the current scale. For 600 parts, the recorded packaging-frequency MILP runtime is 0.382 s, routing is 0.104 s and a five-replication 90-day simulation benchmark is 0.122 s on the execution environment used for the release.

The main computational burden is therefore not a single optimization solve; it is the many stochastic experiments needed to establish robustness. The staged pipeline is an engineering response to that fact.

## 19. Credibility limits and remaining model risk

The final closure deliberately stops adding algorithms. The most important unresolved limitation is empirical validation. Supplier locations, part parameters, cost rates, reliability, damage, returnable loss and service costs are synthetic. The model cannot estimate actual Ferrari/OEM savings without real inputs.

Routing is physical and capacity-feasible but remains heuristic downstream of the exact packaging-frequency block. Inventory simulation is daily, so intra-shift milk-run dynamics and line-side supermarket constraints are simplified. Packaging geometry does not solve full 3-D bin packing with dunnage, orientation, center-of-gravity and load-securing constraints. TTS/TTR are synthetic exposure proxies. Emissions factors are methodological defaults rather than measured carrier data. The financial model does not resolve commercial ownership or Incoterm allocation.

These are not hidden defects. They define the context of use: comparing policy architecture and demonstrating a defensible engineering workflow under synthetic conditions.

## 20. Industrial data required for external validation

A real deployment would require at least six data families. First, carrier invoice/rate-card data and actual lane fill to recalibrate transport economics. Second, supplier ASN/receipt timestamps and OTIF decomposition to fit lead-time severity and correlation. Third, packaging drawings, dunnage rules, actual pack quantities, damage records and line-side footprint constraints. Fourth, dock timestamps and labor standards to validate receiving queues. Fifth, container scans, dwell times, losses and repair histories to calibrate the reverse loop. Sixth, shortage, premium-freight and line-stop histories to estimate actual service economics.

With those data, the most important validation questions would be predictive: does the model reproduce observed lane utilization, receipt variability, stockout frequency, container turnaround and disruption recovery? Until then, the appropriate label remains a research-grade synthetic study.

## 21. Management recommendation

Management should not choose the absolute nominal minimum solely because it is cheapest in expected synthetic operating cost. The nominal joint policy costs EUR 47.86M and Target+ costs EUR 47.98M, a difference of only EUR 126.3k per year. That small premium buys stronger critical-part protection and materially lower line-stop exposure across the scenario set.

The recommended policy is therefore Target+, subject to real-data calibration before capital approval. The first management focus should be on carrier-capacity contingency, demand-shock planning and returnable availability, because those mechanisms dominate the severe failure region. The second focus should be empirical data collection in the high-VOI categories rather than algorithmic complexity.

The final decision statement is intentionally conservative: **a robust 9% saving against a credible baseline is much stronger than a fragile 40% saving against a weak baseline.**

## References and methodological anchors

1. ISO 14083:2023, *Greenhouse gases - Quantification and reporting of greenhouse gas emissions arising from transport chain operations*. https://www.iso.org/standard/78864.html
2. Smart Freight Centre, *GLEC Framework*, road-freight WTW accounting guidance and default factors. https://www.smartfreightcentre.org/
3. AIAG, *Returnable Containers Management Guideline RC-5-2*. https://www.aiag.org/training-and-resources/manuals/details/RC-5
4. AIAG, packaging and labeling resources for automotive supply-chain standardization and traceability. https://www.aiag.org/
5. MIT Center for Transportation & Logistics, 2025 inbound logistics planning capstone on hub location and supplier pickup scheduling. https://ctl.mit.edu/
6. MIT supply-chain resilience work describing Time to Recover and Time to Survive concepts and their industrial application. https://cee.mit.edu/
7. Recent Transportation Research / EJOR / Computers & Industrial Engineering literature cited in `docs/research_basis.md` for dock-capacity, VRPTW, automotive milk-run and disruption-mitigation context.

**Evidence rule:** these sources support method selection and terminology only. They do not validate the synthetic network parameters or final savings percentage.

## Appendix A - Final policy table

| Policy | TLC / year | Critical fill | P(line stop) | Transport CO2e |
|---|---:|---:|---:|---:|
| Baseline A | EUR 81.82M | 99.9913% | 60.0% | 3.337 kt |
| Baseline B | EUR 52.92M | 99.9926% | 75.0% | 3.884 kt |
| Sequential | EUR 51.25M | 99.9892% | 63.3% | 3.347 kt |
| Nominal joint | EUR 47.86M | 99.9912% | 70.0% | 3.347 kt |
| Target+ robust | EUR 47.98M | 99.9991% | 6.7% | 3.347 kt |

## Appendix B - Cost bridge

| cost_component                |   baseline_b_eur |   target_plus_eur |   saving_eur |
|:------------------------------|-----------------:|------------------:|-------------:|
| transport_eur                 |       6128449.76 |        5334177.44 |    794272.31 |
| packaging_material_eur        |      13724196.10 |        9481222.37 |   4242973.73 |
| packaging_cleaning_repair_eur |       2072232.07 |        2632471.81 |   -560239.74 |
| reverse_logistics_eur         |       2790422.11 |        3323839.37 |   -533417.26 |
| inventory_eur                 |       3140746.91 |        3554174.21 |   -413427.30 |
| handling_eur                  |      20930920.30 |       20280151.20 |    650769.10 |
| damage_eur                    |        221508.48 |         200961.71 |     20546.76 |
| dock_wait_eur                 |       3482844.80 |        2930680.71 |    552164.09 |
| dock_overtime_eur             |         95655.30 |         120841.48 |    -25186.19 |
| premium_freight_eur           |        309954.20 |         123768.63 |    186185.57 |
| line_stop_exposure_eur        |         24938.90 |           1691.05 |     23247.85 |

## Appendix C - Out-of-sample summary

| policy         | scenario   |   fill_rate |   critical_fill_rate |   line_stop_probability |   mean_line_stop_events |   premium_freight_events |   p95_shortage_duration_days |   mean_disruption_cost_eur |
|:---------------|:-----------|------------:|---------------------:|------------------------:|------------------------:|-------------------------:|-----------------------------:|---------------------------:|
| Nominal joint  | carrier    |    0.994878 |             0.998737 |                1.000000 |               12.800000 |              1351.080000 |                     3.000000 |             1205195.717354 |
| Nominal joint  | combined   |    0.978787 |             0.989648 |                1.000000 |               76.400000 |              7058.440000 |                     4.000000 |             7338307.998184 |
| Nominal joint  | container  |    0.997414 |             0.999611 |                1.000000 |                4.760000 |               967.360000 |                     3.000000 |              711716.289015 |
| Nominal joint  | correlated |    0.998668 |             0.999932 |                0.800000 |                1.440000 |               419.880000 |                     2.000000 |              282067.142389 |
| Nominal joint  | demand10   |    0.996272 |             0.999628 |                0.960000 |                4.480000 |              1558.440000 |                     3.000000 |             1070560.890124 |
| Nominal joint  | nominal    |    0.998764 |             0.999914 |                0.480000 |                0.720000 |               401.240000 |                     2.000000 |              262226.083570 |
| Target+ robust | carrier    |    0.996581 |             0.999680 |                0.960000 |                3.160000 |               898.960000 |                     3.000000 |              654538.121281 |
| Target+ robust | combined   |    0.982393 |             0.994658 |                1.000000 |               43.600000 |              5746.920000 |                     4.000000 |             5265785.524077 |
| Target+ robust | container  |    0.998284 |             0.999973 |                0.560000 |                0.680000 |               610.320000 |                     3.000000 |              387824.334580 |
| Target+ robust | correlated |    0.999288 |             1.000000 |                0.000000 |                0.000000 |               210.920000 |                     3.000000 |              125844.014314 |
| Target+ robust | demand10   |    0.997599 |             0.999963 |                0.360000 |                0.520000 |               944.200000 |                     3.000000 |              586443.990867 |
| Target+ robust | nominal    |    0.999321 |             1.000000 |                0.000000 |                0.000000 |               201.120000 |                     3.000000 |              121548.231505 |

## Appendix D - Stress suite

| scenario                     |   annual_cost_eur |   fill_rate |   critical_fill_rate |   line_stop_probability |   mean_line_stop_events |   premium_freight_events_mean |   p95_shortage_duration_days | policy         |
|:-----------------------------|------------------:|------------:|---------------------:|------------------------:|------------------------:|------------------------------:|-----------------------------:|:---------------|
| nominal                      |   47863623.364612 |    0.998737 |             0.999898 |                0.666667 |                1.333333 |                    403.300000 |                     2.000000 | Nominal joint  |
| demand_plus_20pct            |   50608934.064017 |    0.992533 |             0.998854 |                1.000000 |               14.266667 |                   4194.166667 |                     3.000000 | Nominal joint  |
| critical_supplier_disruption |   47849809.478285 |    0.998783 |             0.999932 |                0.500000 |                1.000000 |                    386.300000 |                     2.000000 | Nominal joint  |
| container_shortage           |   48879712.653587 |    0.995765 |             0.999326 |                1.000000 |                7.033333 |                   1704.000000 |                     3.000000 | Nominal joint  |
| carrier_capacity_shortage    |   51035870.531015 |    0.986265 |             0.994150 |                1.000000 |               50.200000 |                   2912.200000 |                     4.000000 | Nominal joint  |
| combined_shock               |   65770026.655689 |    0.952835 |             0.967306 |                1.000000 |              219.166667 |                  13532.200000 |                     4.000000 | Nominal joint  |
| fuel_plus_50pct              |   50530712.085859 |    0.998737 |             0.999898 |                0.666667 |                1.333333 |                    403.300000 |                     2.000000 | Nominal joint  |
| nominal                      |   47977994.053401 |    0.999338 |             0.999997 |                0.100000 |                0.100000 |                    197.600000 |                     2.000000 | Target+ robust |
| demand_plus_20pct            |   49704129.484083 |    0.994646 |             0.999733 |                0.933333 |                3.466667 |                   2832.966667 |                     3.000000 | Target+ robust |
| critical_supplier_disruption |   47985128.754787 |    0.999360 |             0.999999 |                0.033333 |                0.033333 |                    207.266667 |                     2.550000 | Target+ robust |
| container_shortage           |   48662263.368094 |    0.997035 |             0.999779 |                0.800000 |                2.366667 |                   1177.633333 |                     3.000000 | Target+ robust |
| carrier_capacity_shortage    |   50073189.189889 |    0.988834 |             0.997203 |                1.000000 |               23.833333 |                   2286.300000 |                     4.000000 | Target+ robust |
| combined_shock               |   63264050.801112 |    0.957440 |             0.973423 |                1.000000 |              178.066667 |                  12154.033333 |                     4.000000 | Target+ robust |
| fuel_plus_50pct              |   50645082.774647 |    0.999338 |             0.999997 |                0.100000 |                0.100000 |                    197.600000 |                     2.000000 | Target+ robust |

## Appendix E - Test closure

Final automated suite: **42 passed, 0 failed**. See `tests/test_final_closure.py` for release-specific reconciliation and credibility tests and `outputs/FINAL_QA_REPORT.md` for the final audit.
