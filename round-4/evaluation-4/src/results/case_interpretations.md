# Case interpretations: rooting shown at the level of single host entries

The cases are the two frozen k=2 medoids plus, for each, the nearest non-medoid with a different origin group (exp8 `cases_selection.json`). They were picked by the quantitative result, not by fame. Numbers come from `results/cases_rooting.json` and `results/case_entries.csv`. A_cont is the mean pre-entry host share of the entry-year partners, taken from D2's stored values (independently re-derived in exp_7). An entry counts as rooted when EST_bin = 1. The co-primary sample means at least 5 partners and complete controls.

## Wireless backhaul (BROAD medoid, Computer Science, F = 2006, lead-lag "neither")
Wireless backhaul is broad from its first year. In 2007 its 3-year window already splits 59/38 between Computer Networks and Electrical Engineering. By 2022 Electrical Engineering leads (60%), Aerospace Engineering has grown to 19%, and 7 subfields are active. The concept's strength percentile rises from 47 to 69. It stays a peripheral node in Guimerà-Amaral terms (P 0.31-0.40, wmz below 0), and its betweenness percentile climbs to 92. Its role path is mostly OTHER.

This is occupancy at scale: 14 host entries, all in the co-primary sample, spread over Aerospace, Biomedical Engineering, Education, Transportation, Political Science and others. Only one entry is rooted, Aerospace Engineering in 2008. That entry has the highest host share of all (A_cont 0.084, graft label *anchored*, 6 newcomer W2 papers). The 13 non-rooted entries average A_cont 0.021, and most of them arrive as origin packages (CT 0.6-1.0).

Within this concept, the rooted entry had the higher host share (+0.062). Breadth came from many shallow entries, and rooting happened only where the partners already spoke the host language.

## Einstein-Podolsky-Rosen steering (BROAD, nearest non-medoid, Physics, F = 2011, expansion_only; expansion onset 2013)
EPR steering starts split between Artificial Intelligence (50%) and Atomic/Molecular Physics and Optics (40%). The AI share is plausibly an OpenAlex topic-classifier artefact on quantum-information papers. The concept then stays in that pair: 68/27 in 2022, with 2-3 active subfields. It is a connector (R3; P 0.63-0.72) and a robust BRIDGE almost every year. Its strength percentile rises from 20 to 54, and its betweenness percentile from 80 to 93.

Of its 7 co-primary entries, one is rooted: AI in 2011. That entry has A_cont 0.142, an anchored graft label, CT 0 and 37 newcomer papers. The 6 non-rooted entries average A_cont 0.027. Four of them have CT at or above 0.55, and they target distant hosts (Molecular Biology, Astronomy, Modeling).

Rooted-minus-unrooted A_cont is +0.115. So a BROAD type label can hide a concept whose integration rests on a single well-anchored entry. The typology counts the reach, but only the anchored entry took root.

## Locally repairable code (LOCALISED medoid, Computer Science, F = 2013, lead-lag "neither")
Locally repairable code stays at 84-96% in Computer Networks and Communications for its whole life. H_rar is 0.13 in 2014 and 0.32 in 2022, with at most 2 active subfields. The concept is kinless-to-peripheral (P 0.80 to 0.61) and a robust BRIDGE every year, because its co-word neighbourhood spans coding theory, storage systems and networks. Community-level bridging and disciplinary breadth are separate things.

It has only 3 host entries. Two of them (Information Systems and Management, Philosophy) have fewer than 5 partners and fall outside the co-primary sample. The one co-primary entry, AI in 2013 (A_cont 0.056, CT 0.20, 3 newcomer papers), is rooted. With no non-rooted co-primary entry there is no contrast, and the case shows rooting without occupancy.

## Holographic QCD (LOCALISED, nearest non-medoid, Physics, F = 2006, expansion_only; expansion onset 2007)
Holographic QCD stays at 95-97% in Nuclear and High Energy Physics from 2007 to 2022. It expands quickly inside its community: the strength percentile goes from 64 to 88 by 2009 and betweenness sits at the 95th-98th percentile. It is a connector (R3) and a robust BRIDGE during expansion. Structural expansion without disciplinary diffusion is exactly the expansion_only category.

Its 5 co-primary entries (Geochemistry, Computational Mechanics, Astronomy, Atomic/Molecular Physics and Optics, Spectroscopy, 2007-2010) are all non-rooted. They average A_cont 0.041, and three of them have CT 1.0: pure origin packages. Even the entry with the highest host share (AMO physics, A_cont 0.132) did not establish. No entry is rooted, so there is no rooted-versus-unrooted contrast.

This is the absence stated: a locally concentrated concept whose excursions are packaged imports that do not take root.
