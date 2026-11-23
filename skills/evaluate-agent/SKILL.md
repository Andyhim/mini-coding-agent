---
name: evaluate-agent
description: Check the Lab 4 Q-learning vacuum agent for vacuum_world_lab3.ipynb, writing lab4_solution.py first if needed, by reviewing the algorithm, running experiments against value iteration, and summarizing the results for the write-up.
triggers: q-learning, reinforcement learning, vacuum agent, evaluate agent, experiment, value iteration
---
Write (if needed), review, and evaluate the Q-learning agent for the vacuum
world. The code goes in `lab4_solution.py` in the workspace root. Never edit
`vacuum_world_lab3.ipynb`.

## Environment

- The grid is a 2D list. Cells: "start" (start cell), "goal" (terminal,
  reward +10), -1 (trap, terminal, reward -1), "X" (obstacle, cannot be
  entered), any other number (reward for entering that cell).
- This is pathfinding: the agent learns to reach the goal. There is no dirt,
  cleaning, or Suck action.
- The state is the agent's cell `(row, col)`. Actions: Up, Down, Left, Right.
- A move goes the intended way with 80% probability and to each
  perpendicular side with 10%. Moving into "X" or off the grid leaves the
  agent in place.
- Each move earns the entered cell's reward plus the living cost, except when
  entering the goal or a trap.
- Episodes start at "start" and end at the goal, at a trap, or after 100 steps.

The notebook's Lab 3 code is loaded before `lab4_solution.py`, so
`GridWorldMDP`, `value_iteration`, and `run_episode` already exist. Do not
redefine them. Use the environment `env` only through:

- `env.start`: the start state
- `env.actions`: `['Up', 'Down', 'Left', 'Right']`
- `env.all_states()`: every state except obstacles
- `env.is_terminal(s)`: True for the goal and traps
- `env.transition(s, a)`: a list of `(next_state, probability)` pairs
- `env.get_reward(s2)`: the reward for entering `s2` (living cost included)
- `env.gamma`: the discount factor

## Required interface

`lab4_solution.py` must start with `import random` and define:

    def q_learning(env, n_episodes, alpha, epsilon):
        ...
        return q, policy

- `q[s][a]` is a number for every state `s` in `env.all_states()` and every
  action `a` in `env.actions`.
- `policy[s]` is the action with the highest `q[s][a]` for each non-terminal
  state, and `None` for terminal states.
- Put any demo code under `if __name__ == "__main__":`.

## Reference algorithm (standard tabular Q-learning)

    initialize Q(s, a) = 0 for every state s and action a
    for each episode:
        s = start state
        for up to 100 steps, until s is terminal:
            choose a with epsilon-greedy: a random action with probability
                epsilon, otherwise an action with the highest Q(s, a)
            sample s2 from the env.transition(s, a) outcomes
            r = env.get_reward(s2)
            if s2 is terminal: target = r
            else: target = r + gamma * max over a2 of Q(s2, a2)
            Q(s, a) = Q(s, a) + alpha * (target - Q(s, a))
            s = s2
    policy(s) = the action with the highest Q(s, a)

## Steps

0. If `lab4_solution.py` does not exist, write it with write_file, following
   the interface and the reference algorithm. Keep it short and simple.
1. Review: read `lab4_solution.py` and check each item below. If one fails,
   fix it with patch_file before going on.
   - The target uses the max over the next state's actions (not the next
     action actually taken, which would be SARSA).
   - A terminal next state adds no future value.
   - The next state is sampled from `env.transition`, not assumed to be the
     intended cell.
   - All four actions are possible in every non-terminal state.
   - Q keeps its values across episodes, and each episode stops after 100
     steps.
   - Each update uses the right `s`, `a`, `r`, and `s2`.
   - The policy picks the highest-valued action in each state.
2. Experiment: run this with run_shell and `"timeout": 120`:

       py -3 skills/evaluate-agent/scripts/evaluate.py --seeds 5

   Start with the script's default settings, plus any settings the user
   gave. If it prints `ERROR:`, fix `lab4_solution.py` and run it again. To
   compare settings, change only one of `--alpha`, `--epsilon`, or
   `--episodes` at a time, and keep at least 5 seeds.
3. Decide: the agent has learned the task when the last line is
   `VERDICT: learned`. That means, for all three living costs (0, -0.1, -1),
   averaged over at least 5 seeds:
   - its goal rate is within 1 percentage point of the value iteration policy
   - its mean value error is below 0.5

   Exact policy matches are reported but not required, because some cells
   have nearly tied moves. If the verdict is "not learned", fix the code or
   change one setting, then repeat step 2. Stop after 3 tries and report
   what failed.
4. Final answer:
   - the review result, with any accepted design choices
   - the results table, with the exact settings and seeds
   - whether the agent meets the definition above
   - two or three sentences the user can adapt for the write-up
