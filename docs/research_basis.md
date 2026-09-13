# Research Basis — Automotive Supplier Packaging & Inbound Logistics Optimization

## Scope
This repository is a **research-grade synthetic automotive inbound logistics and packaging optimization study**. External sources support methodology and terminology; they do **not** validate the synthetic parameter values or numerical results.

## Methodological anchors

1. **ISO 14083:2023**, *Greenhouse gases — Quantification and reporting of greenhouse gas emissions arising from transport chain operations*. ISO states that the standard establishes a common methodology for quantifying and reporting GHG emissions from freight and passenger transport chains. https://www.iso.org/standard/78864.html
2. **Smart Freight Centre, GLEC Framework v3.2 (2025)**. GLEC is aligned with ISO 14083 and is used here as the conceptual basis for activity-based freight emissions accounting. https://smartfreightcentre.org/news/13311209
3. **GLEC Framework v3.0 road defaults**. For European road freight with limited operational data, GLEC provides starting-point WTW intensities including roughly 115 g CO2e/t-km for HGV >20 t; the framework explicitly notes these are starting values and unlikely to be exactly right for a specific operation. https://www.smartfreightcentre.org/documents/328/GLEC_FRAMEWORK_v3_UPDATED_02_04_24.pdf
4. **AIAG Returnable Containers Management Guideline RC-5-2**. AIAG explicitly treats financial considerations, container selection, identification, allocation, tracking, and maintenance as parts of returnable-container management. https://www.aiag.org/training-and-resources/manuals/details/RC-5
5. **AIAG JAIF Global Guideline for Returnable Transport Items**. Provides automotive-industry guidance on data carriers and traceability for RTIs. https://www.aiag.org/training-and-resources/manuals/details/RC-6
6. **AIAG Packaging & Labeling resources**. AIAG describes standardized packaging/pallet/container approaches as mechanisms to improve delivered quality, logistics efficiency, traceability, and physical cube utilization. https://china.aiag.org/expertise-areas/supply-chain-management/packaging---labeling
7. **MIT CTL (2025), Strategic Inbound Logistics Planning**. A recent industrial capstone illustrates the value of combining hub-location and supplier pickup-scheduling decisions; its reported ~50% distance reduction and 80% contracted-truck utilization are case-specific evidence, not benchmarks imported into this model. https://ctl.mit.edu/publications/strategic-inbound-logistics-planning-cross-business-approach-hub-location-and-supplier
8. **Computers & Operations Research (2024), multi-trip VRPTW with capacitated unloading station**. Supports explicitly modeling receiving/unloading capacity rather than treating the plant dock as infinite. DOI/source: https://www.sciencedirect.com/science/article/pii/S0305054824001606
9. **IFAC-PapersOnLine (2024), CVRP with scheduled arrival, time windows, split delivery and emissions**. Supports joint economic/environmental routing formulations with capacity and time-window realism. https://www.sciencedirect.com/science/article/pii/S2405896324001940
10. **Integrated car sequencing and vehicle routing in automotive mixed-model assembly (2024/2025)**. Documents use of milk-run logistics for synchronized automotive parts supply and its trade-off against point-to-point/cross-dock alternatives. https://www.sciencedirect.com/science/article/pii/S0360835224008325
11. **MIT supply-chain resilience work**. MIT describes Time-to-Recover (TTR) as time for a node to return to full function and Time-to-Survive (TTS) as the maximum disruption duration for which supply can continue to match demand. The approach was applied at Ford. https://cee.mit.edu/companies-use-mit-research-to-identify-and-respond-to-supply-chain-risks/
12. **Raaymann & Spinler (2024), automotive supply-chain resilience measurement**. Highlights delivery performance, volume flexibility and stock levels as relevant resilience dimensions in automotive value chains. https://www.sciencedirect.com/science/article/pii/S1366554524003831
13. **2025 disruption-mitigation study in Computers & Industrial Engineering**. Examines hybrid strategies such as multi-sourcing, backup suppliers, reserved inventory and alternate shipment strategies under regional disruption probabilities. https://www.sciencedirect.com/science/article/pii/S0360835225006618
14. **Automotive packaging life-cycle model (2020)**. Demonstrates that returnable-versus-expendable packaging decisions depend jointly on packaging, warehousing and transport cost and can reverse as distance/demand changes. https://www.mdpi.com/2071-1050/12/22/9431

## Rules derived from the literature
- Never optimize freight distance without payload, cube and time feasibility.
- Never treat returnables as free reusable assets: fleet size, reverse flow, cleaning, repair, loss and capital must be modeled.
- Never interpret a default emissions factor as plant-specific empirical truth.
- Separate nominal efficiency from disruption resilience.
- Use TTS/TTR as operational exposure indicators, not as a decorative composite score.
- Treat a cross-dock as an economic decision with handling/capacity costs, not an automatic improvement.

## Evidence boundary
No Ferrari, OEM, carrier or supplier data are represented. Geometry, demand, costs, reliabilities and operating constraints are synthetic. External research supports the **model design**, not the **numerical answers**.
