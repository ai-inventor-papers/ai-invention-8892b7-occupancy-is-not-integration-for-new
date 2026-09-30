# Codebook: emerging-concept-capable scientific terms

You label candidate phrases mined from titles and abstracts of scientific articles (OpenAlex, 2003-2016).
Each item gives a normalised key, the surface forms seen in text, an acronym long form if one was detected,
and up to 3 context snippets. Judge from the phrase and the snippets ONLY. Ignore how famous or widespread
the term became later: a term that stayed obscure and a term that became huge get the same label if they
are the same kind of thing.

## Labels

**CONCEPT**: a specific, reusable scientific notion that several independent papers could share as a named
object of study. It can be a method, model, algorithm, material, compound, organism or strain, gene or protein,
phenomenon, task, dataset, instrument, theory, disease entity or clinical construct. Examples: *graph neural network*,
*perovskite solar cell*, *CRISPR interference*, *microRNA-21*, *metabolic syndrome*, *technology acceptance model*.

**NOT_CONCEPT**: compositional, discourse or study-specific phrases, not a shared named object. This covers
evaluative or methodological filler (*previous studies*, *significant increase*, *the proposed approach*, *present study*,
*this paper*), study-specific entities (a particular sample, site or cohort), measurements, quantities, numbers,
units, dates, person or place names used as study context, publisher boilerplate (*Elsevier Ltd*, *all rights reserved*),
and noun phrases that are just a generic head plus an arbitrary modifier (*water sample*, *second group*).

**TOO_GENERIC**: a genuine scientific term that is too broad to be an emerging concept, such as a whole field,
a basic entity class or a ubiquitous variable. Examples: *machine learning*, *protein*, *temperature*, *patients*,
*cancer*, *model*, *algorithm*, *gene expression*, *climate change*, *students*.

**VARIANT_OF**: the item is only a surface variant (plural, hyphenation, acronym vs long form, British/American
spelling, word order) of ANOTHER item in the SAME batch. Give that item's id in `variant_of`. Use it only when the
two items name the same thing. When unsure, label the item on its own merits instead.

## Decision rules
1. If the phrase is boilerplate, a number or unit, a person or place name, or evaluative filler, answer NOT_CONCEPT.
2. If it names a whole discipline or an everyday or basic class used across all of science, answer TOO_GENERIC.
3. If it names a specific reusable technique, material, entity, phenomenon or construct, answer CONCEPT, including
   multi-word technical terms that are rare.
4. Confidence: 3 = clear, 2 = probable, 1 = guess.

## Few-shot examples
- "support vector regression" (snippet: "...we used support vector regression to predict...") → CONCEPT
- "metal-organic framework" → CONCEPT
- "zebrafish model" (snippet: "...a zebrafish model of epilepsy...") → CONCEPT
- "brain-derived neurotrophic factor" → CONCEPT
- "previous studies" → NOT_CONCEPT
- "significant difference" → NOT_CONCEPT
- "Elsevier B.V." → NOT_CONCEPT
- "second experiment" → NOT_CONCEPT
- "machine learning" → TOO_GENERIC
- "patients" → TOO_GENERIC
- items k3 = "svr" (acronym, long form "support vector regression") and k1 = "support vector regression" in the same batch → k3: VARIANT_OF, variant_of = "k1"
