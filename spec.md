# Specification: Agent Skills Component

**SDLC stage:** 2 of 5 — Specification (intend.md → **spec.md** → plan.md → implementation + tests → report.md)
**Traces to:** success criteria S1–S7 in `intend.md`

Requirements use **MUST** / **SHOULD** / **MAY** (RFC 2119). Each one has an ID that tests and `report.md` refer back to.

---

## 1. Definitions

| Term | Meaning |
|------|---------|
| **Skill** | A folder holding a `SKILL.md` file that describes a reusable procedure |
| **Skills directory** | A top-level workspace folder named `skills/`, `skill/`, or `.skills/` |
| **Catalog** | The list of every discovered skill's `name: description` |
| **Active skill** | The skill whose full instructions are currently in the agent's prompt |
| **Similarity check** | The scoring of a prompt against every skill to decide whether one should trigger |

---

## 2. Skill file format

**R-FMT-1** A skill MUST be stored at `<workspace>/<skills-dir>/<skill-folder>/SKILL.md`. The filename match MUST be case-insensitive (`skill.md` is also accepted).

**R-FMT-2** `SKILL.md` MAY start with a frontmatter block between `---` lines, holding `key: value` pairs:

```markdown
---
name: pr-review
description: Review a pull request or code diff for bugs, style issues, and missing tests
triggers: review, pull request, diff, code review
---
1. Run `git diff` to see the changes.
2. List bugs, style issues, and missing tests.
3. Return a review summary.
```

| Field | Required | Default | Use |
|-------|----------|---------|-----|
| `name` | No | folder name | Unique ID; used by `use_skill` and for explicit mentions |
| `description` | Recommended | `""` | Shown in the catalog; used for similarity |
| `triggers` | No | none | Comma-separated keywords; used for similarity |

**R-FMT-3** Everything after the frontmatter MUST be treated as the skill's **instruction body**.

**R-FMT-4** Parsing MUST NOT require any third-party library (no PyYAML).

---

## 3. Functional requirements

### 3.1 Discovery (→ S1)

**R-DISC-1** At agent startup, the component MUST scan every skills directory that exists and register each valid skill.

**R-DISC-2** A folder without a `SKILL.md` MUST be skipped silently.

**R-DISC-3** If no skills are found, the agent MUST behave exactly like the original agent: no `use_skill` tool, and the catalog shows `- none`.

### 3.2 Prompt-triggered activation (→ S2, S3)

**R-TRIG-1** On every user request (`MiniAgent.ask`), the component MUST run a similarity check between the request and every skill before the first model call.

**R-TRIG-2** Similarity MUST be the **cosine similarity of TF-IDF vectors**:
- **Prompt document:** the user request
- **Skill document:** `name` (with hyphens turned into spaces) + `description` + `triggers`
- **Tokenization:** lowercase, alphanumeric tokens, stopwords removed, tokens longer than 1 character
- **IDF:** `1 + ln((N + 1) / (1 + df))` over the skill documents

**R-TRIG-3** If the request contains a skill's name (e.g. `pr-review` or `/pr-review`), that skill's score MUST be set to **1.0** (explicit invocation).

**R-TRIG-4** The highest-scoring skill MUST be activated if its score is **≥ 0.20** (the `SKILL_THRESHOLD` constant). Otherwise no skill is activated.

**R-TRIG-5** If no skill has been activated yet in the current agent instance, the prompt MUST contain `Active skill: none`. A skill that is already active stays active on later requests until another skill replaces it (R-EXEC-4).

### 3.3 Agent-triggered activation (→ S4)

**R-TOOL-1** When at least one skill exists, the agent MUST expose a tool:

```
use_skill(name: str) [safe] — Load an agent skill's SKILL.md instructions by name and follow them.
```

**R-TOOL-2** `use_skill` MUST be marked **not risky** (no approval prompt), since it only reads.

**R-TOOL-3** Validation MUST reject an unknown skill name with an error that lists the available skills.

**R-TOOL-4** On success, the tool MUST activate the skill and return its instruction body as the tool result.

### 3.4 Execution / context injection

**R-EXEC-1** The stable prompt prefix MUST include the **catalog only** (names and descriptions), never full skill bodies. This preserves prefix cache reuse (component 2).

**R-EXEC-2** When a skill is active, its full body MUST be injected into the *dynamic* part of the prompt, after memory and before the transcript, in this form:

```
Active skill: <name> (from <relative path>)
Follow these instructions step by step:
<body>
```

**R-EXEC-3** Activation MUST add the note `skill active: <name>` to working memory (component 5).

**R-EXEC-4** Only one skill MAY be active at a time. A new activation replaces the previous one.

### 3.5 Logging (→ S5)

**R-LOG-1** Every log entry MUST be appended as one JSON object per line (JSONL) to `<workspace>/.mini-coding-agent/skills.log`. The directory MUST be created if it is missing.

**R-LOG-2** Every similarity check MUST log:

```json
{"created_at": "<ISO-8601 UTC>", "event": "similarity_check", "source": "prompt",
 "prompt": "<full user request>", "scores": {"<skill>": 0.6489, "...": 0.0},
 "threshold": 0.2, "selected": "<skill name or null>"}
```
`scores` MUST include **every** skill, sorted from highest to lowest.

**R-LOG-3** Every activation (by prompt or by tool) MUST log:

```json
{"created_at": "<ISO-8601 UTC>", "event": "skill_executed",
 "trigger": "prompt | agent", "skill": "<name>", "path": "skills/<folder>/SKILL.md"}
```

---

## 4. Non-functional requirements

**R-NF-1 Dependencies:** Python standard library only.
**R-NF-2 Compatibility:** All existing tests MUST still pass (→ S6). The CLI flags and session format MUST NOT change.
**R-NF-3 Testability:** All behavior MUST be testable with `FakeModelClient` (no Ollama needed).
**R-NF-4 Performance:** Similarity checks SHOULD take under 10 ms for 50 or fewer skills.
**R-NF-5 Transparency:** Every trigger decision MUST be reconstructable from `skills.log` alone.

---

## 5. Acceptance tests

| Test (`tests/test_skills.py`) | Requirements | Criterion |
|-------------------------------|--------------|-----------|
| `test_discovers_skill_folder` | R-DISC-1, R-TOOL-1, R-EXEC-1 | S1 |
| `test_prompt_triggers_skill_and_logs` | R-TRIG-1–4, R-EXEC-2, R-LOG-2, R-LOG-3 | S2, S5 |
| `test_unrelated_prompt_does_not_trigger` | R-TRIG-4, R-TRIG-5, R-LOG-2 | S3 |
| `test_agent_can_invoke_skill_mid_task` | R-TOOL-1–4, R-LOG-3 | S4 |
| Existing `tests/test_mini_coding_agent.py` | R-NF-2 | S6 |
| Live Lab 4 run (documented in `report.md`) | all | S7 |

---

## 6. Known limitations (accepted for this version)

- **Lexical matching only:** Paraphrased prompts that share no words with a skill won't trigger it automatically. The mitigations are `triggers`, explicit mention, and the `use_skill` fallback.
- **Explicit-mention matching is a substring check:** A skill with a very short name could match by accident inside unrelated words. Use descriptive, hyphenated names.
- **Skills are sticky within a run:** In interactive mode, a skill stays active on later unrelated requests until another one replaces it. A future version could clear the active skill when a new request scores below the threshold.
- **Active skill is not saved with the session:** On `--resume`, the skill is chosen again by the next prompt.
- **Small local models** may not follow skill steps faithfully. This is model behavior, not a component defect, and it is recorded in `report.md`.
