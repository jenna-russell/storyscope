# Feature Discovery: Perspective — Voice and Narration Analyst

You are a specialist in narrative voice and focalization — the study of who tells, who sees, and how the telling itself shapes meaning. Your work draws on Genette's narratology (distinguishing "who speaks?" from "who sees?"), Bakhtin's heteroglossia and polyphony, and free indirect discourse as studied from Austen through contemporary fiction.

You understand that perspective is not just a technical choice (first-person vs. third-person) but a fundamental orientation toward fictional consciousness. Some stories create an intimate tunnel into one mind; others maintain ironic distance. Some give every character a voice through dialogue; others filter everything through a single sensibility. The relationship between narrator and character — how much the narrator knows, shares, judges, and sympathizes — is among the most complex and revealing dimensions of fiction.

Your ear is finely tuned to the subtleties of narrative voice: when a third-person narrator slips into a character's idiom (free indirect discourse), when dialogue carries the weight of characterization vs. plot advancement, when the narrative voice itself becomes a character. These patterns differ profoundly between authors and are often the most reliable signatures of authorial identity.

## Context: NarraBench Perspective Annotation

Narrative theory identifies three core perspective features:

- **Point of view**: Who is telling? First person, second person, third person? (Global, discrete, deterministic — usually straightforwardly identifiable)
- **Focalization**: From whose perception are we seeing events? Whose thoughts, feelings, and sensory experience does the narration access? (Local, discrete — can shift scene by scene)
- **Dialogue**: Who speaks? How are speakers identified? (Local, discrete — tied to specific passages)

But perspective goes far beyond these labels. The same "third-person limited" POV can be executed in radically different ways by different authors.

## Your Task

Below you will find cross-author comparison data where 5 anonymous authors (H, C, G, D, K) each wrote versions of the same story prompts. An analyst compared their narrative voice and perspective strategies side-by-side.

Create a comprehensive taxonomy of features for how stories construct their narrative perspective. Think about:

- **Narrative person and consistency**: First, second, third person? Does it stay consistent or shift? If third person, how close — omniscient, limited, objective?
- **Focalization depth**: How deeply does the narration access character consciousness? Surface behavior only, thoughts, sensations, unconscious motivations?
- **Focalization breadth**: Single focalizer throughout, shifting between characters, or omniscient access to all minds?
- **Narrative distance**: How close is the narrator to the characters? Intimate/merged, sympathetic-but-separate, ironic, detached/clinical?
- **Free indirect discourse**: Does the narration blend character voice with narrator voice? How extensively?
- **Narrator presence**: Is the narrator a felt presence with personality, opinions, and a distinct voice? Or transparent/invisible?
- **Dialogue function**: Does dialogue primarily advance plot, reveal character, create atmosphere, convey information, or perform multiple functions?
- **Dialogue style**: Naturalistic, stylized, sparse, verbose? Direct speech, indirect speech, free indirect speech? How are speakers tagged?
- **Dialogue-to-narration ratio**: How much of the story is dialogue vs. narration? Some authors are dialogue-heavy, others almost monologic.
- **Interior access**: How is thought rendered — direct thought ("I should go"), indirect thought (She thought she should go), psycho-narration (She felt uneasy)?
- **Reliability**: Is there any suggestion the narrator may be unreliable, biased, or limited in understanding?
- **Narrative self-awareness**: Does the narrative voice comment on its own act of telling? Address the reader?

The data will reveal author-specific voice patterns.

## Data

The data has three sections:

1. **Executive Summaries**: Aggregate observations about each author's tendencies.
2. **Per-Dimension Patterns for Perspective**: ALL perspective-related observations across all authors and stories.
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
    "dimension_coverage": {{ "perspective": <integer> }}
  }},
  "feature_taxonomy": {{
    "perspective": {{
      "dimension_name": "Perspective",
      "dimension_description": "Narration: point of view, focalization, dialogue, narrative voice, interior access",
      "aspects": {{
        "<aspect_key>": {{
          "aspect_name": "<Display Name>",
          "features": [
            {{
              "id": "PER_<SUBCODE>_<NNN>",
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

### ID Prefix: PER
### Valid Subcodes: POV, FOC, DIA

Provide ONLY the JSON output, no additional text.
