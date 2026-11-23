"""PostToolUse hook: report syntax errors in a notebook's code cells.

Exit code 2 sends the error message on stderr back to Claude.
"""
import json
import sys


def strip_magics(source):
    """Blank out IPython magic and shell lines, keeping line numbers."""
    lines = source.split("\n")
    return "\n".join(
        "" if line.lstrip().startswith(("%", "!")) else line
        for line in lines
    )


def find_syntax_errors(notebook):
    """Return one message for each code cell that does not compile."""
    errors = []
    for index, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "code":
            continue
        source = strip_magics("".join(cell["source"]))
        try:
            compile(source, f"cell {index}", "exec")
        except SyntaxError as error:
            errors.append(f"cell {index}, line {error.lineno}: {error.msg}")
    return errors


def main():
    hook_input = json.load(sys.stdin)
    path = hook_input["tool_input"]["notebook_path"]
    with open(path, encoding="utf-8") as notebook_file:
        errors = find_syntax_errors(json.load(notebook_file))
    if errors:
        print("Syntax errors in notebook:", *errors, sep="\n", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
