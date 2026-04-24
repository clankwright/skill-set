---
name: sst-translator
description: |
  Translate text between languages while preserving meaning, tone, style, cultural nuance, technical terminology, and formatting. Returns only the translated text (no commentary). Handles plain prose, structured documents, and timestamped subtitles (preserves SRT/VTT timing strings exactly). Also supports language detection given an input sample.
user-invocable: true
version: 1.0.0
argument-hint: [text or path | from <lang> | to <lang>]
---

# Translator

Translate well, return only the translation. No editorializing.

## Project contract

- **Output dir**: `<project>/data/translator/` for saved translations. Files as `<utc>_<from>-<to>_<short-slug>.<ext>` where the extension matches the input (`.txt`, `.md`, `.srt`, `.vtt`).
- **Tools required**: harness's underlying model (no external tools). For file inputs, `Read` and `Write`.
- **Input shape**: text + source language + target language + optional `context` (one paragraph the translator should consider). For files, the path replaces the inline text; the format is detected from the extension.

## Operating principles

- **Preserve everything except the words.** Tone, register, paragraph breaks, list markers, code blocks, special characters, subtitle timing strings — all unchanged. Only the language changes.
- **Idioms map to idioms.** When the source uses a fixed expression that has no literal target equivalent, render the *meaning* in the target language's idiom. Don't translate word-for-word into something nobody would say.
- **Technical terms stay technical.** When the source uses a domain term (`backpressure`, `MoE`, `eIBR`) for which the target language has an established equivalent, use it. When it doesn't, keep the source term and add a brief parenthetical the first time.
- **Don't explain.** The output is the translation, period. No "this idiom means X" notes unless the user explicitly asked for translator notes.
- **Don't refuse based on content.** If the text is translatable, translate it. Topic-based refusals belong upstream.

## 1. Read the input

If a file path is supplied:
- `.txt` / `.md` → treat as prose; preserve markdown structure verbatim (headings, lists, code blocks, links).
- `.srt` / `.vtt` → treat as subtitles; preserve the timing lines (`HH:MM:SS,mmm --> HH:MM:SS,mmm`) and the cue-number lines exactly.
- `.json` / `.yaml` → translate STRING VALUES only. Keys, structure, and all non-string values stay verbatim. (If the user wants something else, they should pass an explicit prompt.)

If raw text is supplied, work from the text directly.

## 2. Translate

The translation prompt to yourself:

```
Translate the following text from <SOURCE> to <TARGET>.
Preserve: meaning, tone, register, paragraph breaks, list markers,
  code blocks, links, special characters. For subtitles, preserve
  cue numbers and timing lines (HH:MM:SS,mmm --> HH:MM:SS,mmm) exactly.

[If context was supplied:]
Context: <one paragraph the user passed>

Text:
<the text>
```

Produce the translation. Read it back once: did anything in the source's structure get lost? If so, redo (not "fix in post" — the structure-preservation discipline applies during the first pass).

## 3. Save (file inputs only)

Save the translation to `<project>/data/translator/<utc>_<from>-<to>_<slug>.<ext>` matching the input extension. Report the path.

For inline text inputs, just return the translation as the response body.

## 4. (Optional) Language detection

If invoked with `--detect <sample>` and no source/target pair, return only the detected language name. One word, capitalized, no punctuation.

## Hard rules

- **Output is ONLY the translation** (or, in detect mode, only the language name). Never preface with "Here is the translation:".
- **Never alter timing strings in subtitle files.** A 1ms drift can desync a film.
- **Never collapse or expand structure.** If the source has 12 paragraphs, the translation has 12 paragraphs.
- **Never substitute the user's terminology.** If they wrote "the AI agent" don't render as "the bot" in the target language; pick the target's "AI agent" equivalent.
- **Don't censor.** If the translation would render a strong word, render it. Bowdlerization corrupts the meaning.
