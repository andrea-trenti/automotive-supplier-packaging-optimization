# Recruiter Brief

## Repository description

Research-grade synthetic automotive inbound logistics study jointly coordinating packaging, replenishment, routing, inventory and returnable-container flows under uncertainty; delivers a 9.33% robust total-landed-cost saving against a smart baseline.

## Suggested GitHub topics

`automotive` `supply-chain` `operations-research` `logistics` `inventory-optimization` `vehicle-routing` `packaging-engineering` `monte-carlo` `risk-analysis` `python` `sustainability`

## CV bullets

- Built a stochastic automotive inbound-logistics framework across **60 suppliers, 600 parts and 57 Target+ routes**, coordinating packaging, replenishment, milk-runs, docks, inventory and returnable loops; reduced modeled total landed cost from **EUR 52.92M to EUR 47.98M**, a **9.33% robust saving** against a smart baseline.
- Red-teamed an initial **40.2% weak-baseline saving** into a defensible result through out-of-sample disruption testing, physical-capacity validation and **42/42 automated tests**; quantified **-13.83% transport CO2e vs smart baseline**, **150,272 operational returnables**, and **EUR 6.39M median 5Y NPV** within the synthetic uncertainty range.

## 60-90 second interview story

I built the project around a realistic inbound automotive decision rather than a standalone routing problem. The system links 60 suppliers and 600 parts to packaging choices, shipment frequency, milk-runs, receiving docks, inventory and returnable-container loops. My first model appeared to save about 40%, but that comparison used a weak baseline. I deliberately challenged it by creating a smarter benchmark with compatible packaging, supplier clustering, simple milk-runs and ROP inventory. The defensible saving dropped to 9.33%, which I consider a stronger result because it survived a credible comparison. I then compared sequential optimization with a coordinated joint policy and created a robust Target+ that costs only 0.26% more than the nominal optimum but materially reduces modeled line-stop risk. The main remaining failure region is a combined carrier-capacity, demand and container-availability shock. The project taught me that the best industrial answer is not the largest saving or the cheapest mathematical optimum; it is the policy that remains defensible when physical constraints and uncertainty are added.

## Recommended interview structure

**Weak baseline -> smarter benchmark -> joint coordination -> robust Target+ -> stress failure region.**

The strongest point is methodological discipline: the project reduced its own headline saving from roughly 40% to 9.33% when the benchmark became more credible, instead of protecting the original result.
