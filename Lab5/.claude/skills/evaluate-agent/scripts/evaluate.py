"""Train the notebook's Q-learning agent and compare it with value iteration.

Example:
    python3 evaluate.py --alpha 0.05 --epsilon 0.9 --episodes 5000 --seeds 5
"""
import argparse
import json
import os
import random

import numpy as np

REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
)
NOTEBOOK = os.path.join(REPO_ROOT, "vacuum_world_lab3.ipynb")
GRID = [
    [0, 0, 0, 'start'],
    [0, 'X', 0, 0],
    [0, 0, 0, 0],
    [0, -1, 0, 'goal'],
]


def load_notebook_code():
    """Run the Lab3 and Lab5 code cells and return their definitions.

    __name__ is not "__main__" here, so the MAIN cells do not run.
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
            exec(source, namespace)
    return namespace


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
    q, policy = code["q_learning"](
        env,
        n_episodes=args.episodes,
        alpha=args.alpha,
        epsilon=args.epsilon,
    )
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
        "goal_rate": code["goal_rate"](env, policy, args.eval_episodes),
        "best_goal_rate": code["goal_rate"](
            env, best_policy, args.eval_episodes
        ),
        "steps": mean_steps(code, env, policy, args.eval_episodes),
        "best_steps": mean_steps(code, env, best_policy, args.eval_episodes),
    }


def main():
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

    code = load_notebook_code()
    print(
        f"alpha={args.alpha} epsilon={args.epsilon} gamma={args.gamma} "
        f"episodes={args.episodes} seeds=0..{args.seeds - 1}"
    )
    print(
        "living_cost  goal_rate  optimal  start_err  mean_err  policy_match"
        "  steps  optimal_steps"
    )
    for living_cost in args.living_costs:
        runs = [
            evaluate(code, living_cost, args, seed)
            for seed in range(args.seeds)
        ]
        average = {
            key: sum(run[key] for run in runs) / len(runs) for key in runs[0]
        }
        print(
            f"{living_cost:>11} {average['goal_rate']:>10.1%} "
            f"{average['best_goal_rate']:>8.1%} "
            f"{average['start_error']:>10.2f} "
            f"{average['mean_error']:>9.2f} "
            f"{average['policy_matches']:>7.1f}/{runs[0]['n_states']}"
            f"{average['steps']:>9.2f} {average['best_steps']:>14.2f}"
        )


if __name__ == "__main__":
    main()
