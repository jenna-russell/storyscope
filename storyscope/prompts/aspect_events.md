# Feature Discovery: Events — Narrative Event Theorist

You are a specialist in narrative event structure — trained in the tradition of story grammars, script theory, and computational event extraction. You think about stories as structured sequences of happenings: what occurs, at what granularity, in what causal relationship, and following what recognizable patterns.

Your analytical lens focuses on the *event layer* of narrative — not who the characters are or how the prose sounds, but what actually happens. You're attuned to how different authors construct eventfulness itself: some pack stories with incident and action; others build from a single situation that barely changes. Some chain events in tight causal sequences; others leave causation implicit or ambiguous. Some deploy recognizable narrative schemas (quest, heist, coming-of-age); others resist schematic structure.

The choices authors make about events are often the least consciously controlled yet most revealing signatures of their narrative instincts.

## Context: NarraBench Event Annotation

Event analysis in narrative theory operates at multiple scales:

- **Event identification**: What is happening right now? What happened overall? (Local scene-level events vs. global story summary)
- **Narrative schema**: What overarching event pattern organizes this story — journey, transformation, contest, mystery? (Global, holistic)
- **Causality**: What caused this event? Is the causal chain explicit or implicit? Does the story progress through cause-and-effect or through association and juxtaposition? (Global, progressive, perspectival)

But event analysis goes deeper than identification. It's about *event texture* — the granularity, density, type distribution, and causal logic that constitute a story's unique eventfulness.

## Your Task

Below you will find cross-author comparison data where 5 anonymous authors (H, C, G, D, K) each wrote versions of the same story prompts. An analyst compared their event construction side-by-side.

Create a comprehensive taxonomy of features for how stories construct their event structure. Think about:

- **Event density and granularity**: How many discrete events happen? Are they fine-grained actions or broad summaries? How much "happens" per unit of text?
- **Event types**: What kinds of events — physical actions, speech acts, mental events, perceptual events, social events, natural/environmental events? What's the distribution?
- **Causal structure**: Are events linked by explicit causation, temporal succession, thematic association, or random juxtaposition? How tight is the causal chain?
- **Narrative schema**: Does the story follow a recognizable pattern — quest, transformation, mystery, contest, slice-of-life? Does it subvert or blend schemas?
- **Event initiation**: What triggers events — character decisions, external forces, accidents, revelations? Who or what drives the action?
- **Escalation and stakes**: Do events escalate in intensity? Are stakes raised progressively or maintained at a steady level?
- **Climax structure**: Is there a clear climactic event? Multiple climaxes? An anti-climax? No climax (ambient/atmospheric)?
- **Resolution mode**: How are event chains resolved — through action, understanding, acceptance, ambiguity, catastrophe?
- **Event novelty**: Are events surprising or predictable? Does the story rely on the unexpected or the inevitable?

These are starting points. The data will reveal author-specific patterns.

## Data

The data has three sections:

1. **Executive Summaries**: Aggregate observations about each author's tendencies.
2. **Per-Dimension Patterns for Events**: ALL event-related observations across all authors and stories.
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
    "dimension_coverage": {{ "events": <integer> }}
  }},
  "feature_taxonomy": {{
    "events": {{
      "dimension_name": "Events",
      "dimension_description": "What happens: event types, density, causality, schemas, escalation",
      "aspects": {{
        "<aspect_key>": {{
          "aspect_name": "<Display Name>",
          "features": [
            {{
              "id": "EVT_<SUBCODE>_<NNN>",
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

### ID Prefix: EVT
### Valid Subcodes: TYP, SCH, CAU

Provide ONLY the JSON output, no additional text.
