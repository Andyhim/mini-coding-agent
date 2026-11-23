"""Acceptance tests for component 7, Agent Skills (spec.md section 5)."""
import json

from mini_coding_agent import (
    FakeModelClient,
    MiniAgent,
    SessionStore,
    SkillRegistry,
    WorkspaceContext,
)

PR_REVIEW = """---
name: pr-review
description: Review a pull request or code diff for bugs, style issues, and missing tests
triggers: review, pull request, diff, code review
---
1. Run `git diff` to see the changes.
2. List bugs, style issues, and missing tests.
3. Return a review summary.
"""

# Keeps a Claude Code-only key to check that unknown keys are ignored (R-FMT-5).
EVALUATE_AGENT = """---
name: evaluate-agent
description: Check the Q-learning agent by reviewing the algorithm, running experiments, and summarizing the results
triggers: q-learning, evaluate, experiment, reinforcement learning
disable-model-invocation: true
---
1. Read lab4_solution.py.
2. Run the experiment script.
"""


def write_skill(root, folder, text, skills_dir="skills", filename="SKILL.md"):
    path = root / skills_dir / folder / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def write_both_skills(root):
    write_skill(root, "pr-review", PR_REVIEW)
    write_skill(root, "evaluate-agent", EVALUATE_AGENT)


def build_agent(root, outputs, approval_policy="auto"):
    (root / "README.md").write_text("demo\n", encoding="utf-8")
    workspace = WorkspaceContext.build(root)
    store = SessionStore(root / ".mini-coding-agent" / "sessions")
    return MiniAgent(
        model_client=FakeModelClient(outputs),
        workspace=workspace,
        session_store=store,
        approval_policy=approval_policy,
    )


def log_path(root):
    return root / ".mini-coding-agent" / "skills.log"


def read_log(root):
    lines = log_path(root).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def test_discovers_skill_folder(tmp_path):
    write_skill(tmp_path, "pr-review", PR_REVIEW)
    # Another skills directory and a lowercase file name (R-FMT-1).
    write_skill(tmp_path, "evaluate-agent", EVALUATE_AGENT, skills_dir=".skills", filename="skill.md")
    # A folder without SKILL.md is skipped silently (R-DISC-2).
    (tmp_path / "skills" / "notes").mkdir()

    agent = build_agent(tmp_path, [])

    assert isinstance(agent.skills, SkillRegistry)
    assert sorted(skill.name for skill in agent.skills.skills) == ["evaluate-agent", "pr-review"]
    assert agent.active_skill is None
    assert "use_skill" in agent.tools
    assert agent.tools["use_skill"]["risky"] is False
    # The prefix holds the catalog only, never a skill body (R-EXEC-1).
    assert "- pr-review: Review a pull request or code diff" in agent.prefix
    assert "- evaluate-agent: Check the Q-learning agent" in agent.prefix
    assert "Run `git diff`" not in agent.prefix
    assert "Read lab4_solution.py" not in agent.prefix

    # Without skills the agent behaves like the original one (R-DISC-3).
    empty_root = tmp_path / "empty"
    empty_root.mkdir()
    plain = build_agent(empty_root, ["<final>ok</final>"])
    assert plain.skills.skills == []
    assert "use_skill" not in plain.tools
    assert "Agent skills (call use_skill when one fits the task):\n- none" in plain.prefix
    assert plain.ask("Please review the pull request diff") == "ok"
    assert not log_path(empty_root).exists()


def test_prompt_triggers_skill_and_logs(tmp_path):
    write_both_skills(tmp_path)
    agent = build_agent(tmp_path, ["<final>Reviewed.</final>"])
    request = "Please review the pull request diff for bugs"

    answer = agent.ask(request)

    assert answer == "Reviewed."
    assert agent.active_skill.name == "pr-review"
    assert "skill active: pr-review" in agent.session["memory"]["notes"]

    # The body is in the dynamic part: after memory, before the transcript (R-EXEC-2).
    prompt = agent.model_client.prompts[0]
    assert "Active skill: pr-review (from skills/pr-review/SKILL.md)\nFollow these instructions step by step:\n1. Run `git diff`" in prompt
    assert prompt.index("Memory:") < prompt.index("Active skill: pr-review") < prompt.index("Transcript:")

    check, executed = read_log(tmp_path)
    assert check["event"] == "similarity_check"
    assert check["source"] == "prompt"
    assert check["prompt"] == request
    assert check["threshold"] == 0.2
    assert check["selected"] == "pr-review"
    # Every skill is scored, highest first (R-LOG-2).
    assert list(check["scores"]) == ["pr-review", "evaluate-agent"]
    assert check["scores"]["pr-review"] >= 0.2 > check["scores"]["evaluate-agent"]
    assert check["created_at"]

    assert executed["event"] == "skill_executed"
    assert executed["trigger"] == "prompt"
    assert executed["skill"] == "pr-review"
    assert executed["path"] == "skills/pr-review/SKILL.md"
    assert executed["created_at"]

    # Naming a skill is an explicit invocation and scores 1.0 (R-TRIG-3).
    scores = agent.skills.scores("run /evaluate-agent on my code")
    assert scores["evaluate-agent"] == 1.0
    assert next(iter(scores)) == "evaluate-agent"


def test_unrelated_prompt_does_not_trigger(tmp_path):
    write_both_skills(tmp_path)
    agent = build_agent(tmp_path, ["<final>Done.</final>"])

    agent.ask("Write a function that adds two numbers")

    assert agent.active_skill is None
    assert "Active skill: none" in agent.model_client.prompts[0]
    entries = read_log(tmp_path)
    assert len(entries) == 1
    assert entries[0]["event"] == "similarity_check"
    assert entries[0]["selected"] is None
    assert set(entries[0]["scores"]) == {"pr-review", "evaluate-agent"}
    assert all(score < 0.2 for score in entries[0]["scores"].values())


def test_agent_can_invoke_skill_mid_task(tmp_path):
    write_both_skills(tmp_path)
    # approval_policy="never" proves use_skill needs no approval (R-TOOL-2).
    agent = build_agent(
        tmp_path,
        [
            '<tool>{"name":"use_skill","args":{"name":"no-such-skill"}}</tool>',
            '<tool>{"name":"use_skill","args":{"name":"evaluate-agent"}}</tool>',
            "<final>Evaluated.</final>",
        ],
        approval_policy="never",
    )

    answer = agent.ask("Write a function that adds two numbers")

    assert answer == "Evaluated."
    tool_events = [item for item in agent.session["history"] if item["role"] == "tool"]
    # An unknown name is rejected with the list of available skills (R-TOOL-3).
    assert tool_events[0]["content"].startswith("error: invalid arguments for use_skill")
    assert "evaluate-agent" in tool_events[0]["content"]
    assert "pr-review" in tool_events[0]["content"]
    # A valid call activates the skill and returns its body (R-TOOL-4).
    assert "1. Read lab4_solution.py." in tool_events[1]["content"]
    assert agent.active_skill.name == "evaluate-agent"
    assert "Active skill: evaluate-agent" in agent.model_client.prompts[2]

    entries = read_log(tmp_path)
    assert [entry["event"] for entry in entries] == ["similarity_check", "skill_executed"]
    assert entries[0]["selected"] is None
    assert entries[1]["trigger"] == "agent"
    assert entries[1]["skill"] == "evaluate-agent"
    assert entries[1]["path"] == "skills/evaluate-agent/SKILL.md"
