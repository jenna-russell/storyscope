You are a narrative analysis expert. Extract a comprehensive outline from the provided narrative text by answering the questions below. Analyze the text systematically and provide specific evidence for each element identified.

## Instructions
- Be objective and avoid interpretation beyond what the text explicitly or implicitly conveys
- Use null for information not present in the narrative or fields with no applicable items
- For trajectories and sequences, use arrows (->) to show progression: "state1 -> state2 -> state3". Remember, trajectories and sequences are not always linear, but always have to be complete.
- Keep descriptions concise but specific.
- **Scale guidance**: 
  - **Global** fields require story-level analysis across the entire narrative
  - **Local** fields require scene-level or moment-specific analysis (indicate which scene/moment when relevant)

## Narrative
{narrative_text}

## Extraction object schema
Return a JSON object with the following schema:
{
  "story": {
    "agents": {
      "major_characters": [
        {
          "name": (string) [GLOBAL] Use the character's full name as-is,
          "role": (string) [GLOBAL] Describe the character's narrative and functional role in the story (max 2 short clauses),
          "attributes": (array of strings) [GLOBAL] Extract any phrases that describe the character's personality, physical traits, etc.,
          "emotion_trajectory": (string) [GLOBAL] Describe the character's initial emotion -> progression -> final emotion across the story,
          "motivation_trajectory": (string) [GLOBAL] Describe the character's initial motivation -> progression -> final motivation across the story, 
          "trope": (string) [GLOBAL] Describe a character's trope or archetype, if any
        }
        (list only major characters who drive the plot or have significant narrative importance)
      ],
      "supporting_characters": [
        {
          "name": (string) [GLOBAL] Use the character's full name as-is,
          "description": (string) [GLOBAL] One-line description of the character's role and significance
        }
        (list supporting and minor characters who appear meaningfully but are not central to the plot. Omit background extras unless referenced by name/role.)
      ]
    },
    "social_network": {
      "relationships": (list) [GLOBAL] Describe enduring bonds across the story as "A-B: relationship type and quality",
    },
    "events": {
      "sequence": [
        {
          "who": (string or list) Name(s) of characters or groups who participate,
          "where": (string) Specific location/setting of the event,
          "what": (string) Concisely describe the concrete event or beat,
          "when": (string) Time elapsed or narrative time placement (e.g., "at dawn", "later that night", "after confrontation")
        }
        (list all concrete, beat-by-beat events in order as they occur in the narrative. Each event is [LOCAL] - scene-level/local)
      ],
      "causality": (list) [GLOBAL] For each causal relationship, describe as "event1 -> event2: causal explanation",
      "narrative_schema": (string) [GLOBAL] Describe the higher-level narrative schema or pattern that structures the events (e.g., quest, revenge, coming-of-age, etc.)
    },
    "plot": {
      "themes": (list) [GLOBAL] Describe the main themes of the story,
      "summary": (string) [GLOBAL] Brief plot summary in 2-3 sentences,
      "moral": (string) [GLOBAL] Include a single sentence if the text signals it; else null,
      "central_obstacle": (string) [GLOBAL] The main negative force or challenge,
      "central_conflict": (string) [GLOBAL] The primary conflict driving the narrative,
      "narrative_archetype": (string) [GLOBAL] Describe the narrative archetype, if any,
      "plot_arc": (string) [GLOBAL] Describe the plot arc structure (e.g., "rising action -> climax -> falling action" or other arc pattern)
    },
    "setting": {
      "locations": (list) [LOCAL/GLOBAL] Include both scene-specific locations and overall story locations. For each, specify if it's a scene-level or story-level location,
      "time_period": (string) [GLOBAL] When the story takes place (historical period, era, etc.),
      "atmosphere": (string) [GLOBAL] Overall mood or atmosphere of the setting across the story
    }
  },
  "discourse": {
    "revelation": {
      "suspense": (string) [GLOBAL] What key information is withheld to create tension across the narrative,
      "curiosity": (string) [GLOBAL] What causal antecedents or explanations are being withheld to create curiosity,
      "surprises": (list) [GLOBAL] For each surprise item, describe what was revealed and when in the narrative,
    },
    "temporal_order": {
      "structure": (string) [GLOBAL] Choose from: linear / nonlinear / mixed, 
      "duration": (string) [GLOBAL] Overall time span of the narrative (e.g., "a single day", "several months", "years"),
      "flashbacks": (list) [LOCAL] Extract any moments that interrupt present time, specifying which scenes are flashbacks,
      "time_jumps": (list) [LOCAL] Short clauses for ellipses or leaps in time/place, specifying the scenes involved,
      "scene_duration": (list) [LOCAL] For major scenes, note approximate duration or time elapsed (e.g., "Scene 1: several hours", "Scene 2: a few minutes")
    }
  },
  "narration": {
    "perspective": {
      "point_of_view": (string) [GLOBAL] Choose from: 1st person / 2nd person / 3rd person limited / 3rd person omniscient, 
      "focalization": (list) [LOCAL] For each scene or section, specify which character(s) perspective we experience (e.g., "Scene 1: Character A", "Scene 2: Character B"),
      "dialogue_speakers": (list) [LOCAL] List all named characters who speak dialogue, organized by scene or section,
    },
    "style": {
      "allusions": (list) [LOCAL] List key allusions to real-world entities, events, or concepts, noting which scenes/sections they appear in,
      "figurative_language": (list) [LOCAL] List key figurative language used in the text, with examples and scene context,
      "imagery": (list) [LOCAL] List key vivid sensory descriptions, noting which scenes they appear in,
      "sentence_complexity": (string) [GLOBAL] Describe the overall complexity of the sentence structure across the narrative,
      "evaluative_language": (list) [LOCAL] List key examples of judgmental/evaluative language, noting which scenes/sections they appear in,
    }
  } 
}