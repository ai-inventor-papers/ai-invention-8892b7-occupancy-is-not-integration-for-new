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
| 0 | 14 | 2.00 | 29.50 (9) | 28.33 | 1.604 | 0.04 | broad from the start (rapid interdisciplinary) |
| 1 | 73 | 1.50 | 5.00 (17) | 4.17 | 0.134 | 0.17 | gradual broadening |
| 2 | 115 | 1.00 | 2.00 (3) | 1.67 | 0.015 | 0.17 | localised |
