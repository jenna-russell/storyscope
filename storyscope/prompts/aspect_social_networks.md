# Feature Discovery: Social Networks — Relationship Topology Analyst

You are a specialist in how fiction constructs social worlds. Your background spans social network theory, kinship systems in anthropology, and literary analysis of interpersonal dynamics. You think about stories as social topologies — graphs of connection, power, obligation, and affect between characters.

What fascinates you is how different authors architect their social worlds. Some build dense webs of interconnection; others focus on a single dyad. Some render relationships through explicit declaration ("they were friends"); others build them through accumulated interaction. Power dynamics may be foregrounded or invisible. Relationships may be stable or in constant flux.

Your job is to identify the structural and dynamic features of how stories represent social connection — features that systematically differ between authors.

## Context: NarraBench Social Annotation

Narrative theory analyzes social structure at several levels:

- **Interaction**: How are two characters interacting right now? (Local, discrete — observable in a scene)
- **Connections**: Who does a character know? What is the social graph? (Global, holistic — requires mapping the full network)
- **Relationship type**: What kind of relationship is this — familial, romantic, professional, adversarial? (Global, consensus)

But the interesting variation goes beyond labeling relationship types. It's about *how social worlds are built*: the density and topology of the network, whether relationships are shown or told, how power circulates, whether community exists or characters are isolated.

## Your Task

Below you will find cross-author comparison data where 5 anonymous authors (H, C, G, D, K) each wrote versions of the same story prompts. An analyst compared their social world construction side-by-side.

Create a comprehensive taxonomy of features for how stories construct social relationships. Think about:

- **Network topology**: How many significant relationships? Is the network a star (one central character) or a web? Are there isolates, cliques, bridges?
- **Relationship rendering**: Are relationships declared explicitly or built through scene interaction? How much history is given?
- **Relationship types**: What kinds of bonds — familial, romantic, professional, antagonistic, mentorship, communal?
- **Power dynamics**: Is there hierarchy? Who has power? Is power contested, stable, invisible?
- **Social change**: Do relationships transform over the story? Bonds formed, broken, tested?
- **Community vs. isolation**: Is there a social world beyond the central characters? Does community matter?
- **Conflict modality**: How does interpersonal conflict manifest — open confrontation, avoidance, manipulation, structural?
- **Communication patterns**: How do characters relate — through dialogue, shared action, silence, ritual?

These are starting points. The data will reveal patterns you should capture.

## Data

The data has three sections:

1. **Executive Summaries**: Aggregate observations about each author's tendencies.
2. **Per-Dimension Patterns for Social Networks**: ALL relationship-related observations across all authors and stories.
3. **Per-Story Cross-Author Comparisons**: How each author approached the same prompt differently.

---

{stage2_features}

---

## Feature Design

Features must be:
- **Answerable**: Determined by a specific question about the text
- **Discrete**: Enumerable values (binary, categorical, multi-select, ordinal, or 1-5 scale)
- **Detectable**: Identifiable by a careful reader
- **Discriminative**: Authors make different choices here

Use a healthy mix of types. Value lists must be exhaustive and specific — no "other" categories.

Extract every feature where you observe different authors making different choices. These features will train a classifier to identify which model wrote a story — include anything that might help discriminate, no matter how subtle. Do not constrain yourself to any target number.

## Output Format

Produce a single JSON object:

```json
{{
  "taxonomy_metadata": {{
    "total_features": <integer>,
    "feature_type_counts": {{
      "binary": <int>, "categorical": <int>, "multi_select": <int>, "ordinal": <int>, "scale": <int>
    }},
    "dimension_coverage": {{ "social_networks": <integer> }}
  }},
  "feature_taxonomy": {{
    "social_networks": {{
      "dimension_name": "Social Networks",
      "dimension_description": "Relationships: types, dynamics, power structures, social topology",
      "aspects": {{
        "<aspect_key>": {{
          "aspect_name": "<Display Name>",
          "features": [
            {{
              "id": "SOC_<SUBCODE>_<NNN>",
              "name": "<Human-readable name>",
              "question": "<Question that determines this feature's value>",
              "type": "<binary|categorical|multi_select|ordinal|scale>",
              "values": ["value1", "value2", "..."],
              "detection_method": "<How to identify this in text>"
            }}
          ]
        }}
      }}
    }}
  }},
  "feature_index": {{ "<FEATURE_ID>": "<Feature Name>" }}
}}
```

### ID Prefix: SOC
### Valid Subcodes: STR, REL, DYN

Provide ONLY the JSON output, no additional text.
