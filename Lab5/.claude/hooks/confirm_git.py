"""PreToolUse hook: ask the user to confirm git commands.

Only git status, git diff, and git log run without confirmation.
"""
import json
import re
import sys

GIT_COMMAND = re.compile(r"\bgit\b(?:\s+(?:-[Cc]\s+\S+|-\S+))*\s+([\w-]+)")
ALLOWED = {"status", "diff", "log"}


def main():
    hook_input = json.load(sys.stdin)
    command = hook_input["tool_input"].get("command", "")
    to_confirm = [
        name for name in GIT_COMMAND.findall(command) if name not in ALLOWED
    ]
    if to_confirm:
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "ask",
                "permissionDecisionReason":
                    "CLAUDE.md Rule 3: confirm git "
                    f"{', '.join(to_confirm)}.",
            }
        }))


if __name__ == "__main__":
    main()
