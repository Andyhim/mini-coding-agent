---
name: evaluate-agent
description: Check the Lab5 Q-learning agent in vacuum_world_lab3.ipynb by reviewing the algorithm, running experiments, and summarizing the results for the write-up.
disable-model-invocation: true
---

Evaluate the Q-learning agent in the "Lab5 Solution" section of
`vacuum_world_lab3.ipynb`. Run these steps from the main conversation, because
sub agents cannot launch other sub agents. Do not edit the notebook.

## Steps

1. Run the `algorithm-reviewer` sub agent. If it reports a real bug, stop and
   show it to the user. Do not run experiments on incorrect code.
2. Run the `experiment-runner` sub agent. Ask it to test the current settings
   and to change one of `alpha`, `epsilon`, or the episode count at a time.
   Pass along any settings the user gave: $ARGUMENTS
3. Summarize the results using the definition below.

## What "learned" means

The agent has learned the task when, for all three living costs, averaged over
at least 5 seeds:

- its goal rate is within 1 percentage point of the value iteration policy
- its mean value error is below 0.5

Exact policy matches are reported but are not required. Some cells have nearly
tied moves, and a mismatch there does not mean the agent failed.

## Summary format

- The verdict from the reviewer, with any accepted design choices
- A table of results with the exact settings and seeds
- Whether the agent meets the definition above
- Two or three sentences the user can adapt for the write-up
