import random


def q_learning(env, n_episodes, alpha, epsilon):
    """
    Standard tabular Q-learning for the vacuum world pathfinding problem.
    
    Args:
        env: Environment object with methods start, actions, all_states(), 
             is_terminal(s), transition(s, a), get_reward(s2), gamma
        n_episodes: Number of episodes to run
        alpha: Learning rate
        epsilon: Exploration rate
    
    Returns:
        q: 2D array where q[s][a] is the Q-value for state s and action a
        policy: dict mapping states to best action (or None for terminal)
    """
    # Initialize Q-values to 0 for all states and actions
    states = env.all_states()
    actions = env.actions
    
    # Create Q table: q[state_index][action_index]
    q = [[0.0 for _ in range(len(actions))] for _ in range(len(states))]
    
    # Run episodes
    for episode in range(n_episodes):
        s_idx = states.index(env.start)
        s = env.start
        
        for step in range(100):  # Max 100 steps per episode
            # Epsilon-greedy action selection
            if random.random() < epsilon:
                a_idx = random.randint(0, len(actions) - 1)
                a = actions[a_idx]
            else:
                # Find action with max Q-value for current state
                q_values = [q[s_idx][i] for i in range(len(actions))]
                max_q = max(q_values)
                # If tie, pick first one (deterministic for ties)
                a_idx = q_values.index(max_q)
                a = actions[a_idx]
            
            # Sample next state according to transition probabilities
            transitions = env.transition(s, a)
            if not transitions:
                # No valid transitions (shouldn't happen in well-formed MDP)
                break
            
            s2_idx, prob = random.choices(range(len(transitions)), weights=[t[0] for t in transitions])[0]
            s2 = transitions[s2_idx][1]
            
            # Get reward for entering s2
            r = env.get_reward(s2)
            
            # Determine target value
            if env.is_terminal(s2):
                target = r
            else:
                # Find max Q-value for next state
                s2_idx_in_states = states.index(s2)
                max_next_q = max(q[s2_idx_in_states])
                target = r + env.gamma * max_next_q
            
            # Q-learning update
            q[s_idx][a_idx] += alpha * (target - q[s_idx][a_idx])
            
            # Move to next state
            s = s2
            if env.is_terminal(s):
                break
    
    # Extract policy from Q-table
    policy = {}
    for s in states:
        s_idx = states.index(s)
        if env.is_terminal(s):
            policy[s] = None
        else:
            q_values = [q[s_idx][i] for i in range(len(actions))]
            max_q = max(q_values)
            # Pick first action with max Q-value (deterministic for ties)
            a_idx = q_values.index(max_q)
            policy[s] = actions[a_idx]
    
    return q, policy


if __name__ == "__main__":
    # Demo usage
    from vacuum_world_lab3 import GridWorldMDP
    
    env = GridWorldMDP()
    q, policy = q_learning(env, n_episodes=1000, alpha=0.1, epsilon=0.1)
    
    print("Q-learning completed successfully.")
    print(f"Policy for start state: {policy[env.start]}")
