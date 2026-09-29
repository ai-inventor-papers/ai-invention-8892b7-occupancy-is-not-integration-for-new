# Typology naming rule (applied after clustering)

Names come from the median trajectory of `active_subfields_3y` (number of subfields with >= 2 c-papers in the 3-year window)
by concept age, computed per cluster over ages with >= 5 concepts:

1. the cluster with the lowest final level (mean of the last 3 median ages) = **localised**;
2. of the rest, the cluster with the highest start level (mean of ages 0-1), if >= the median start and above
   the localised start = **broad from the start (rapid interdisciplinary)**;
3. any other cluster whose final level is >= 30% below its peak = **temporary expansion**;
4. else positive OLS slope over age = **gradual broadening**; else **stable intermediate**;
5. duplicates are suffixed narrower/broader by final level.

| cluster | n | start | peak (age) | final | slope/yr | drop from peak | name |
|---|---|---|---|---|---|---|---|
| 0 | 59 | 1.50 | 4.00 (17) | 3.50 | 0.080 | 0.12 | gradual broadening (narrower) |
| 1 | 19 | 2.50 | 10.00 (17) | 7.67 | 0.271 | 0.23 | broad from the start (rapid interdisciplinary) |
| 2 | 14 | 1.50 | 33.00 (10) | 24.50 | 2.334 | 0.26 | gradual broadening (narrower) |
| 3 | 110 | 1.00 | 2.00 (3) | 1.67 | 0.011 | 0.17 | localised |
