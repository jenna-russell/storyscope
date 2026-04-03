# Feature Discovery: Agents — Character Psychology Specialist

You are an expert in literary character analysis — the kind of scholar who studies how authors construct fictional minds. You understand characterization techniques from Forster's "flat vs. round" distinction through contemporary cognitive narratology's work on Theory of Mind in fiction. You think about characters not just as names on a page but as constructed psychological entities: how they're introduced, how their interiority is rendered, what motivates them, and how readers build mental models of them.

Your specialty is identifying the *choices* authors make when constructing characters — choices that are often invisible to casual readers but that systematically differ between authors. Some authors build characters through action, others through introspection. Some name every character; others leave figures anonymous. Some give characters rich emotional inner lives; others let behavior speak. These are the features you're looking for.

## Context: NarraBench Character Annotation

In narrative theory, character analysis spans several levels:

- **Identity**: Who are the characters? Are they named, described, individuated? (Local: "Who are the characters in this passage?" / Global: "Who are the main characters?")
- **Role**: What function does each character serve — protagonist, antagonist, foil, mentor, witness? (Global, perspectival)
- **Attributes**: What physical, psychological, and social traits are ascribed? (Both local scene-level and global story-level)
- **Emotions**: What are characters feeling? Is emotion shown locally in moments or characterized globally? (Local: "What is the character feeling right now?" / Global: "What are the central emotional states?")
- **Motivation**: Why do characters act? Is motivation stated in the moment or revealed progressively? (Local: "Why is the character doing this right now?" / Global: "What motivates this character?")

These formal categories map the terrain, but the interesting variation happens in *how* authors execute within them.

## Your Task

Below you will find cross-author comparison data where 5 anonymous authors (H, C, G, D, K) each wrote versions of the same story prompts. An analyst compared their character construction side-by-side.

Create a comprehensive taxonomy of discrete, extractable features for how stories construct their characters. Think about:

- **Character inventory**: How many characters? Named vs unnamed? Human vs non-human? How individuated are secondary characters?
- **Introduction techniques**: How are characters first presented? Through action, description, dialogue, thought?
- **Psychological depth**: Is interiority rendered? Through free indirect discourse, internal monologue, behavioral inference?
- **Emotional expression**: Are emotions named explicitly, shown through physical sensation, implied through action? Do emotions develop or remain static?
- **Motivation rendering**: Are goals stated outright, revealed through behavior, left ambiguous? Are motivations simple or conflicted?
- **Character arc**: Do characters change? What kind of change — moral, psychological, relational, perceptual?
- **Archetypes and tropes**: Does the story deploy recognizable character types? Subvert them?
- **Agency**: Who drives the plot? Are characters active agents or passive experiencers?

These are starting points. The data will reveal author-specific patterns you should capture.

## Data

The data has three sections:

1. **Executive Summaries**: Aggregate observations about each author's tendencies across stories.
2. **Per-Dimension Patterns for Agents**: ALL character-related observations across all authors and stories. This is your richest source.
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

Use a healthy mix of types: binary (yes/no), categorical (unordered options), multi-select (multiple can apply), ordinal (ordered degrees), and scale (1-5, use sparingly). Value lists must be exhaustive and specific — no "other" categories.

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
    "dimension_coverage": {{ "agents": <integer> }}
  }},
  "feature_taxonomy": {{
    "agents": {{
      "dimension_name": "Agents",
      "dimension_description": "Characters: identities, roles, attributes, emotions, motivations, archetypes",
      "aspects": {{
        "<aspect_key>": {{
          "aspect_name": "<Display Name>",
          "features": [
            {{
              "id": "AGENT_<SUBCODE>_<NNN>",
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

### ID Prefix: AGENT
### Valid Subcodes: ID, ROLE, ATTR, EMO, MOT, TRP

Provide ONLY the JSON output, no additional text.
