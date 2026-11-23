import random


def q_learning(env, n_episodes, alpha, epsilon):
    """
    Q-learning for the vacuum agent.
    
    Args:
        env: The GridWorldMDP environment
        n_episodes: Number of episodes to run
        alpha: Learning rate
        epsilon: Exploration rate
    
    Returns:
        q: Dictionary mapping state -> action -> Q-value
        policy: Dictionary mapping state -> best action
    """
    # Initialize Q-values to 0 for all states and actions
    q = {}
    for s in env.all_states():
        for a in env.actions:
            q[s][a] = 0.0
    
    for episode in range(n_episodes):
        s = env.start
        for step in range(100):
            # Epsilon-greedy action selection
            if random.random() < epsilon:
                a = random.choice(env.actions)
            else:
                max_q = max(q[s][a] for a in env.actions)
                actions_with_max = [a for a in env.actions if q[s][a] == max_q]
                a = random.choice(actions_with_max)
            
            # Sample next state from transition model
            s2_list = env.transition(s, a)
            s2, prob = random.choices(s2_list, weights=[p for _, p in s2_list])[0]
            
            # Get reward for entering s2
            r = env.get_reward(s2)
            
            # Determine target value
            if env.is_terminal(s2):
                target = r
            else:
                max_next_q = max(q[s2][a2] for a2 in env.actions)
                target = r + env.gamma * max_next_q
            
            # Update Q-value
            q[s][a] = q[s][a] + alpha * (target - q[s][a])
            
            # Move to next state
            s = s2
    
    # Compute policy by selecting the action with highest Q-value for each non-terminal state
    policy = {}
    for s in env.all_states():
        if env.is_terminal(s):
            policy[s] = None
        else:
            max_q = max(q[s][a] for a in env.actions)
            actions_with_max = [a for a in env.actions if q[s][a] == max_q]
            policy[s] = random.choice(actions_with_max)
    
    return q, policy


if __name__ == "__main__":
    # Demo code can go here
    pass
