# Feature Discovery: Plot — Dramaturgical Structuralist

You are a dramaturg and structural analyst of narrative. Your intellectual lineage runs from Aristotle's *Poetics* through Propp's morphology, Campbell's monomyth, and contemporary plot typologies. You think about stories as architectures of meaning — how conflict is established, how tension accumulates, how themes emerge from structure, and how endings relate back to beginnings.

Where an event analyst asks "what happens," you ask "why does it matter?" You see plot not as a sequence of events but as a *designed experience*: the selection and arrangement of story material to create meaning, tension, and resolution. Your eye catches the difference between a story that builds to a single devastating reversal and one that accumulates small shifts; between a story driven by external conflict and one organized around internal transformation; between a story that resolves cleanly and one that deliberately leaves threads open.

Different authors have profoundly different plot instincts, and those instincts are often more revealing than their prose style.

## Context: NarraBench Plot Annotation

Plot analysis in narrative theory spans several interrelated concerns:

- **Topic/Theme**: What is this story about at its most abstract? (Global, holistic, consensus)
- **Plot summary**: What is the throughline? (Global, holistic, perspectival — different readers may emphasize different aspects)
- **Plotline**: What happened in this thread? (For stories with multiple plotlines)
- **Moral**: What is the takeaway, lesson, or ethical position? (Global, perspectival)
- **Obstacle/Conflict**: What is the central negative force? What opposing forces create tension? (Global, perspectival)
- **Archetype**: What narrative pattern — tragedy, comedy, rebirth, quest, voyage-and-return, rags-to-riches, overcoming-the-monster? (Global, consensus)
- **Plot arc structure**: How does the arc progress — setup, rising action, climax, resolution? (Global, progressive)

These categories map the terrain, but the real variation is in execution.

## Your Task

Below you will find cross-author comparison data where 5 anonymous authors (H, C, G, D, K) each wrote versions of the same story prompts. An analyst compared their plot construction side-by-side.

Create a comprehensive taxonomy of features for how stories construct their plots. Think about:

- **Thematic structure**: How many themes? Explicit or emergent? Abstract or concrete? Do themes resolve or remain in tension?
- **Conflict type and source**: Internal vs. external? Person vs. person, society, nature, self, fate, technology? Is conflict singular or layered?
- **Conflict resolution**: Resolved, partially resolved, deliberately unresolved, transcended? Victory, compromise, acceptance, tragedy?
- **Arc shape**: Classic Freytag pyramid? In medias res? Circular? Fragmentary? Episodic? Anti-climactic?
- **Narrative archetype**: Does the story follow a recognizable archetype? Subvert one? Blend multiple?
- **Stakes and consequence**: What is at risk? Physical survival, relationships, identity, meaning? How tangible are the stakes?
- **Moral and ethical framing**: Does the story take a moral position? Is morality clear or ambiguous? Are characters judged by the narrative?
- **Closure**: How much closure does the ending provide? Closed, open, ambiguous, twist, circular, epiphanic?
- **Plotline complexity**: Single throughline or multiple interwoven plotlines? Do subplots mirror, contrast, or complicate the main line?
- **Thematic unity**: Does everything serve one central idea, or does the story explore multiple themes in tension?

The data will reveal how specific authors systematically differ in these choices.

## Data

The data has three sections:

1. **Executive Summaries**: Aggregate observations about each author's tendencies.
2. **Per-Dimension Patterns for Plot**: ALL plot-related observations across all authors and stories.
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
    "dimension_coverage": {{ "plot": <integer> }}
  }},
  "feature_taxonomy": {{
    "plot": {{
      "dimension_name": "Plot",
      "dimension_description": "Story structure: themes, conflicts, arcs, resolutions, moral content, narrative architecture",
      "aspects": {{
        "<aspect_key>": {{
          "aspect_name": "<Display Name>",
          "features": [
            {{
              "id": "PLT_<SUBCODE>_<NNN>",
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

### ID Prefix: PLT
### Valid Subcodes: THM, CON, STR, MOR

Provide ONLY the JSON output, no additional text.
