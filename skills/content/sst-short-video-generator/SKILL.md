---
name: sst-short-video-generator
description: |
  Generate short cinematic videos (typically 5-10 seconds, with audio) from a text prompt and optional seed image, using whatever video-generation API the project has wired up. Encodes prompt-craft best practices (Subject / Context / Action / Style / Camera / Composition / Ambiance), continuity rules for multi-shot sequences (Append vs Cut), and a storyboard-metadata persistence pattern so multi-shot productions can be regenerated reproducibly. The actual API binding (Veo 3 / Runway / Pika / Sora / etc.) lives in the project's proprietary counterpart.
user-invocable: true
version: 1.0.0
argument-hint: [scene description | --seed-image <path> | --append | --cut]
---

# Short video generator

Drive a video-gen API to render one shot at a time, with structured prompts and consistent continuity between shots. The video-gen API binding is the project's responsibility; this skill names the contract.

## Project contract

- **Output dir**: `<project>/data/sst-short-video-generator/<series-id>/` for individual shot files (typically `.mp4`) and storyboard metadata (`storyboard.json`). `<series-id>` is either user-supplied or auto-generated as `<utc>_<short-uuid>`.
- **Required tool from the project**: a `generate_video(prompt, seed_image_path=None, duration_seconds=8, ...) -> output_path` function (the proprietary counterpart wraps Veo 3, Runway, Pika, Sora, ImagineCraft, etc.). The project's tool returns the path to the rendered file.
- **Required tool**: harness's `Read`, `Write`. Optional: `WebFetch` if seed images are remote URLs that need to be fetched first.
- **Input shape**:
  - **Single shot**: a scene description string + optional `--seed-image <path>`.
  - **Multi-shot**: a sequence of shot descriptions + transition cues per shot (`--append` for continuation, `--cut` for a hard transition).

## Operating principles

- **Structured prompts beat free prose.** Every shot prompt has the same skeleton: Subject, Context, Action, Style, Camera, Composition, Ambiance. Concise (~50 words). Vague prompts produce vague video.
- **Consistency across shots is non-negotiable.** Subjects, props, lighting style, and pacing stay constant unless an explicit `--cut` says otherwise.
- **Use the seed image when provided.** A seed image anchors the visual identity better than any prose description. Always pass it to `generate_video` if available.
- **Save storyboard metadata before rendering.** If a render fails or burns budget, the metadata is enough to retry without losing the prompts.
- **Keep prompts short.** Beyond ~80 words, video models start ignoring or scrambling parts. Cut anything not load-bearing.

## Prompt skeleton

```
Subject:    <who or what is the focus — be specific, e.g. "a 30-year-old
             carpenter with a graying beard, wearing a leather apron">
Context:    <where and when, e.g. "in a sunlit workshop, mid-afternoon">
Action:     <what they're doing, in present continuous, e.g. "running a
             plane along an oak board, shavings curling away">
Style:      <visual style, e.g. "documentary realism, shallow DOF" or
             "Wes Anderson-style symmetric composition">
Camera:     <e.g. "handheld, eye-level, slow drift to the right">
Composition: <e.g. "rule of thirds, subject left third, leading lines
             from the workbench">
Ambiance:  <lighting + mood, e.g. "warm golden hour through the window,
             soft particulate light">
```

## Continuity rules

When generating a sequence, every shot is either an **append** (continues the prior shot's perspective) or a **cut** (intentional shift). Mark which:

### Append (`--append`)

The default for follow-on shots. Preserve from the prior shot:
- Subject identity (same character, same prop, same wardrobe)
- Lighting style (same time of day, same warmth/coolness)
- Pacing (don't suddenly speed up or slow down)
- Camera approach (handheld stays handheld; tripod stays tripod)

Use gentle motion or continuation cues in the prompt: "continuing the same shot, the carpenter ..." or "as the previous frame ends, ...".

### Cut (`--cut`)

Intentional perspective / scene shift. Still preserve subject identity (the carpenter still looks the same), props (the plane still has the same handle), and the visual seed/character bible. What changes: angle, location, possibly time of day. Be explicit in the prompt: "Cut to a different angle: low shot from behind the workbench, ...".

## Process

### 1. Read the input

If single-shot: parse the scene description into the skeleton fields. Ask a clarifying question only if a load-bearing field (Subject or Action) is genuinely missing.

If multi-shot: read each shot's description plus its transition cue. Confirm the series shares a Subject and Style.

### 2. Persist storyboard metadata

Write or update `<output-dir>/<series-id>/storyboard.json`:

```json
{
  "series_id": "<utc>_<uuid>",
  "shots": [
    {
      "index": 0,
      "transition": "first | append | cut",
      "prompt_skeleton": { "Subject": "...", ... },
      "rendered_prompt": "<final string sent to generate_video>",
      "seed_image": "<path or null>",
      "duration_seconds": 8,
      "output_path": "<populated after render>",
      "rendered_at": "<utc, populated after render>"
    },
    ...
  ]
}
```

Storyboard is saved BEFORE the render so a failed render can be retried without re-prompting the user.

### 3. Render each shot

For each shot in order:

1. Compose the final prompt string from the skeleton + transition cue.
2. Call the project's `generate_video(prompt, seed_image_path=..., duration_seconds=...)`.
3. Update the shot record in `storyboard.json` with `output_path` and `rendered_at`.
4. If the render fails: log the error in the shot record (`error: <message>`) and continue to the next shot. Don't abort the whole series — partial success is recoverable.

### 4. Report

```
Series: <series-id>
Shots rendered: <N succeeded> / <N attempted>
Output dir: <path>
Storyboard: <path to storyboard.json>
Failed shots: <list of indices, if any>
```

## Hard rules

- **Never call a video-gen API directly.** Always go through the project's `generate_video` tool. The proprietary counterpart owns the API binding, the auth, the cost tracking.
- **Never send a prompt longer than ~80 words.** Trim ruthlessly.
- **Never render the same shot twice without explicit re-render request.** If a shot's `output_path` is populated and the file exists, skip on a subsequent invocation (treat the storyboard as the source of truth).
- **Don't add safety/ethics commentary to prompts.** The video-gen API has its own filters; bolt-on disclaimers in the prompt either get ignored or degrade output.
- **Never mark a shot succeeded without confirming the output file exists.** Trust but verify.
