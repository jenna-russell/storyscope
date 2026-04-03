You are a literary analyst specializing in `{dimension_name_lower}`.

Extract structured features about **{dimension_name}** from the story below.
Focus area: {dimension_description}

# FEATURES TO EXTRACT

For each feature, select the appropriate value(s) from the allowed options.

**Response format rules:**
- For "binary" features: respond with exactly "yes" or "no"
- For "categorical" features: respond with exactly ONE value from the list
- For "ordinal" features: respond with exactly ONE value from the list
- For "multi_select" features: respond with a JSON array of ALL applicable values
- For "scale" features: respond with an integer within the specified range
- ONLY use values from the provided lists
- If a feature specifies a condition (marked "→ Condition:") that is not met by this story, use the string "n/a"
- **Never use null or omit a key** — every feature must have a value
- If a feature is ambiguous or weakly present, pick the closest-matching value

{features_block}

# STORY TO ANALYZE

<story>
{story_text}
</story>

# OUTPUT

Return a single JSON object with feature IDs as keys. Example format:

```json
{
  "{example_feature_id_1}": "value_here",
  "{example_feature_id_2}": "yes"
}
```

Use "n/a" only for features whose listed condition is not met. Every other feature must have a value from its allowed list.

Return ONLY the JSON object, no other text or explanation.

