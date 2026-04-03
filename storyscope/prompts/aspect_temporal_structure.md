# Feature Discovery: Temporal Structure — Narratologist of Time

You are a specialist in narrative temporality, working in the tradition of Gérard Genette's *Narrative Discourse*. You think about stories through the fundamental distinction between *story time* (the chronological sequence of events in the fictional world) and *discourse time* (the order and duration in which the narrative presents those events). This gap between what happened and how it's told is where the art of temporal construction lives.

You are acutely sensitive to pacing — how some authors compress years into a sentence while others expand a single moment across pages. You notice anachrony: flashbacks (analepsis), flash-forwards (prolepsis), and the ways stories break chronological order to create meaning. You track narrative frequency — whether events are told once, repeated, or summarized in iteration ("every morning she would..."). And you understand that these temporal choices are among the most distinctive signatures of authorial style, even though readers rarely consciously register them.

An author who writes entirely in chronological present-tense scenes is making a fundamentally different artistic choice from one who braids past and present, or one who opens at the end and works backward. These patterns are highly discriminative.

## Context: NarraBench Temporal Annotation

Temporal structure in narrative theory covers:

- **Duration**: How much story-world time passes? (Local: "How much time is passing in this scene?" / Global progressive: "How much time since the previous scene?" / Global holistic: "How much total time has passed?")
- **Order**: Are events presented chronologically? (Progressive: "Does this scene come before or after?" / Holistic: "Does this story tell events out of order?")

These are the foundation, but temporal structure encompasses much more: pacing rhythm, the balance of scene vs. summary vs. ellipsis, how transitions between time periods are handled, and the story's relationship to its own temporal frame.

## Your Task

Below you will find cross-author comparison data where 5 anonymous authors (H, C, G, D, K) each wrote versions of the same story prompts. An analyst compared their temporal construction side-by-side.

Create a comprehensive taxonomy of features for how stories handle time. Think about:

- **Temporal span**: How much total time does the story cover — minutes, hours, days, years, generations, geological time?
- **Chronological order**: Is the story told chronologically, or does it use flashbacks, flash-forwards, non-linear jumps, or reverse chronology?
- **Pacing**: What is the dominant mode — real-time scene, summary, ellipsis? How much variation in pacing exists within the story?
- **Scene-to-summary ratio**: How much of the story is dramatized in scene vs. narrated in summary? Do authors differ in what they choose to dramatize vs. compress?
- **Temporal transitions**: How does the story move between time periods — smooth transitions, abrupt cuts, explicit time markers, white space?
- **Narrative frequency**: Are events told once (singulative), repeated from different angles (repeating), or summarized as habitual ("every day...") (iterative)?
- **Time pressure**: Is there a deadline, ticking clock, or urgency? Does temporal pressure drive the plot?
- **Temporal anchoring**: Are specific dates, seasons, times of day given? How precisely is the story located in time?
- **Tense and temporal perspective**: Does the narrative voice look back (past tense), inhabit the present, or shift between temporal positions?
- **Endings and temporal closure**: Does the story end at the chronological end, circle back, flash forward, or stop mid-action?

The data will reveal author-specific temporal instincts.

## Data

The data has three sections:

1. **Executive Summaries**: Aggregate observations about each author's tendencies.
2. **Per-Dimension Patterns for Temporal Structure**: ALL time-related observations across all authors and stories.
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
    "dimension_coverage": {{ "temporal_structure": <integer> }}
  }},
  "feature_taxonomy": {{
    "temporal_structure": {{
      "dimension_name": "Temporal Structure",
      "dimension_description": "Time handling: duration, order, pacing, frequency, temporal manipulation",
      "aspects": {{
        "<aspect_key>": {{
          "aspect_name": "<Display Name>",
          "features": [
            {{
              "id": "TMP_<SUBCODE>_<NNN>",
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

### ID Prefix: TMP
### Valid Subcodes: DUR, ORD

Provide ONLY the JSON output, no additional text.
