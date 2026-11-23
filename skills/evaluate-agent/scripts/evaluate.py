"""Train the Lab 4 Q-learning agent and compare it with value iteration.

Run from the workspace root:
    py -3 skills/evaluate-agent/scripts/evaluate.py --alpha 0.05 --epsilon 0.9 --episodes 5000 --seeds 5

Ported from the Lab 5 Claude Code skill (.claude/skills/evaluate-agent).
Changes from Lab 5:
- It lives in skills/evaluate-agent/scripts/, so the repo root is three
  levels up instead of four.
- It runs the notebook's Lab 3 cells, then lab4_solution.py. The notebook
  itself is never edited.
- It defines goal_rate and mean_steps here, so the solution only has to
  define q_learning.
- Problems in lab4_solution.py print one ERROR line, and the last line is a
  VERDICT based on the skill's "learned" definition.
"""
import argparse
import json
import os
import random
import sys
import traceback

import numpy as np

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
NOTEBOOK = os.path.join(REPO_ROOT, "vacuum_world_lab3.ipynb")
SOLUTION = os.path.join(REPO_ROOT, "lab4_solution.py")
GRID = [
    [0, 0, 0, 'start'],
    [0, 'X', 0, 0],
    [0, 0, 0, 0],
    [0, -1, 0, 'goal'],
]
# The skill's "learned" definition, averaged over at least MIN_SEEDS seeds.
GOAL_RATE_TOLERANCE = 0.01
MAX_MEAN_ERROR = 0.5
MIN_SEEDS = 5


class SolutionError(Exception):
    """A problem in lab4_solution.py, reported as a single ERROR line."""


def describe(error):
    """Return the error type and message, plus its line in the solution."""
    line = None
    message = str(error)
    if isinstance(error, SyntaxError):
        # str() of a SyntaxError already names the file, so keep the message only.
        message = error.msg
        if error.filename == SOLUTION:
            line = error.lineno
    frames = [
        frame for frame in traceback.extract_tb(error.__traceback__)
        if os.path.abspath(frame.filename) == SOLUTION
    ]
    if frames:
        line = frames[-1].lineno
    where = f" (lab4_solution.py line {line})" if line else ""
    return f"{type(error).__name__}: {message}{where}"


def load_code():
    """Run the Lab 3 code cells, then lab4_solution.py, and return the names.

    __name__ is not "__main__" here, so MAIN cells and demo code do not run.
    """
    with open(NOTEBOOK, encoding="utf-8") as notebook_file:
        cells = json.load(notebook_file)["cells"]
    namespace = {"__name__": "notebook"}
    in_solutions = False
    for cell in cells:
        source = "".join(cell["source"])
        if source.strip() == "# Lab3 Solution":
            in_solutions = True
        elif in_solutions and cell["cell_type"] == "code":
            exec(source, namespace)  # noqa: S102 - running the notebook's code is the point

    if not os.path.isfile(SOLUTION):
        raise SolutionError(
            "lab4_solution.py not found in the workspace root. "
            "Write it first (SKILL.md step 0)."
        )
    with open(SOLUTION, encoding="utf-8") as solution_file:
        source = solution_file.read()
    try:
        exec(compile(source, SOLUTION, "exec"), namespace)  # noqa: S102
    except Exception as error:
        raise SolutionError(
            f"lab4_solution.py failed to load: {describe(error)}"
        ) from error
    if not callable(namespace.get("q_learning")):
        raise SolutionError(
            "lab4_solution.py must define "
            "q_learning(env, n_episodes, alpha, epsilon)."
        )
    return namespace


def check_result(env, result):
    """Check that q_learning returned a usable (q, policy) pair."""
    if not (isinstance(result, tuple) and len(result) == 2):
        raise SolutionError("q_learning must return a (q, policy) tuple.")
    q, policy = result
    for state in env.all_states():
        if env.is_terminal(state):
            continue
        try:
            values = q[state]
            missing = [a for a in env.actions if a not in values]
        except (KeyError, IndexError, TypeError):
            raise SolutionError(
                f"q[{state}] must be a dict of action -> value, "
                "for example q[s]['Up']."
            ) from None
        if missing:
            raise SolutionError(
                f"q[{state}] has no value for {missing}. "
                "Initialize Q(s, a) = 0 for every state and action."
            )
        try:
            action = policy[state]
        except (KeyError, IndexError, TypeError):
            raise SolutionError(
                f"policy has no entry for state {state}."
            ) from None
        if action not in env.actions:
            raise SolutionError(
                f"policy[{state}] is {action!r}, "
                f"but it must be one of {env.actions}."
            )
    return q, policy


def goal_rate(code, env, policy, n_episodes):
    """Return the fraction of episodes in which the policy reaches the goal."""
    wins = 0
    for _ in range(n_episodes):
        path, _ = code["run_episode"](env, policy, verbose=False)
        if path[-1] == env.goal:
            wins += 1
    return wins / n_episodes


def mean_steps(code, env, policy, n_episodes):
    """Return the average number of steps per episode for a policy."""
    total = 0
    for _ in range(n_episodes):
        path, _ = code["run_episode"](env, policy, verbose=False)
        total += len(path) - 1
    return total / n_episodes


def evaluate(code, living_cost, args, seed):
    """Train once and return how the result compares with value iteration."""
    random.seed(seed)
    np.random.seed(seed)
    env = code["GridWorldMDP"](GRID, living_cost=living_cost, gamma=args.gamma)
    try:
        result = code["q_learning"](
            env,
            n_episodes=args.episodes,
            alpha=args.alpha,
            epsilon=args.epsilon,
        )
    except Exception as error:
        raise SolutionError(f"q_learning raised {describe(error)}") from error
    q, policy = check_result(env, result)
    best_values, best_policy = code["value_iteration"](env, verbose=False)

    states = [s for s in env.all_states() if not env.is_terminal(s)]
    errors = [abs(max(q[s].values()) - best_values[s]) for s in states]
    return {
        "start_error": abs(
            max(q[env.start].values()) - best_values[env.start]
        ),
        "mean_error": sum(errors) / len(errors),
        "policy_matches": sum(policy[s] == best_policy[s] for s in states),
        "n_states": len(states),
        "goal_rate": goal_rate(code, env, policy, args.eval_episodes),
        "best_goal_rate": goal_rate(
            code, env, best_policy, args.eval_episodes
        ),
        "steps": mean_steps(code, env, policy, args.eval_episodes),
        "best_steps": mean_steps(
            code, env, best_policy, args.eval_episodes
        ),
    }


def main():
    sys.stdout.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alpha", type=float, default=0.05)
    parser.add_argument("--epsilon", type=float, default=0.9)
    parser.add_argument("--gamma", type=float, default=0.9)
    parser.add_argument("--episodes", type=int, default=5000)
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--eval-episodes", type=int, default=1000)
    parser.add_argument(
        "--living-costs", type=float, nargs="+", default=[0.0, -0.1, -1.0]
    )
    args = parser.parse_args()

    try:
        code = load_code()
        print(
            f"alpha={args.alpha} epsilon={args.epsilon} gamma={args.gamma} "
            f"episodes={args.episodes} seeds=0..{args.seeds - 1}"
        )
        print(
            "living_cost  goal_rate  optimal  start_err  mean_err  "
            "policy_match  steps  optimal_steps  learned"
        )
        failures = []
        for living_cost in args.living_costs:
            runs = [
                evaluate(code, living_cost, args, seed)
                for seed in range(args.seeds)
            ]
            average = {
                key: sum(run[key] for run in runs) / len(runs)
                for key in runs[0]
            }
            gap = round(
                abs(average["goal_rate"] - average["best_goal_rate"]), 6
            )
            learned = (
                gap <= GOAL_RATE_TOLERANCE
                and average["mean_error"] < MAX_MEAN_ERROR
            )
            print(
                f"{living_cost:>11} {average['goal_rate']:>10.1%} "
                f"{average['best_goal_rate']:>8.1%} "
                f"{average['start_error']:>10.2f} "
                f"{average['mean_error']:>9.2f} "
                f"{average['policy_matches']:>7.1f}/{runs[0]['n_states']}"
                f"{average['steps']:>9.2f} {average['best_steps']:>14.2f}"
                f"  {'yes' if learned else 'no'}"
            )
            if not learned:
                failures.append(
                    f"living cost {living_cost}: goal rate {gap:.1%} from "
                    f"optimal, mean error {average['mean_error']:.2f}"
                )
    except SolutionError as error:
        print(f"ERROR: {error}")
        sys.exit(1)

    if args.seeds < MIN_SEEDS:
        print(f"VERDICT: not decided (use --seeds {MIN_SEEDS} or more)")
    elif failures:
        print("VERDICT: not learned (" + "; ".join(failures) + ")")
    else:
        print("VERDICT: learned")


if __name__ == "__main__":
    main()
