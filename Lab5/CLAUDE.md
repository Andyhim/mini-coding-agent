**This document contains critical information about working and interacting with this project. Always follow these guidelines precisely in every action you perform.**

This project aims to implement the Q-learning algorithm to a vacuum agent in a simple simulated environment. The agent's environment is a simple 2D grid, stored as a 2D list in Python. Each cell in the grid contains one of the following:
- "start": the agent's starting cell
- "goal": the recharge station, a terminal cell with a reward of +10
- -1: a trap, a terminal cell with a reward of -1
- "X": an obstacle, the agent cannot move to this cell
- Any other number: the reward for moving to that cell

This is a pathfinding task: the agent learns to reach the goal. The "vacuum" name is carried over from earlier labs, so do not model dirt, cleaning, or a Suck action.

The agent's state is the cell it is currently in.

The agent's available actions are Up, Down, Left, and Right. The agent moves in the intended direction with 80% probability and in each perpendicular direction with 10% probability. A move into an obstacle or off the grid leaves the agent in place. Each move adds the living cost to the reward for the cell entered, except when entering the goal or a trap.

Each episode starts at the "start" cell. An episode ends when the agent reaches the goal or a trap, or after 100 steps.

The project follows the typical structure of an educational Python notebook exploring artificial intelligence concepts. Our task is to add a new "Lab5 Solution" section below the "Lab3 Solution" section and implement the Q-learning algorithm for our vacuum agent there. Write Q-learning as a standalone function, not as an `Agent` class, and reuse the Lab3 code where it fits without changing the Lab3 section. Use `gamma = 0.9` and test living costs of 0, -0.1, and -1, with -0.1 as the final choice. Use `alpha = 0.05`, `epsilon = 0.9`, and 5000 training episodes. These values were chosen through experiments.

**Rules:**

1) Do not install or modify any Python packages.

2) Use PEP 8 style for all Python code written.

3) Explicitly prompt the user to confirm any git operations, especially `commit` and `push`. The only exceptions are `status`, `diff`, and `log`, which do not need confirmation.

4) Write simple, straightforward code that is easy to maintain and understand

5) Don't hide confusion - communicate when you need clarification and if there are tradeoffs, state them

6) Edit only what is necessary and clean up only your own messes