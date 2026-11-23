import random

def q_learning(env, n_episodes, alpha, epsilon):
    # Initialize Q table with zeros for all states and actions
    q = {s: {a: 0.0 for a in env.actions} for s in env.all_states()}
    
    # Policy will be computed at the end
    policy = None
    
    for episode in range(n_episodes):
        s = env.start
        for step in range(100):
            if env.is_terminal(s):
                break
            
            # Epsilon-greedy action selection
            if random.random() < epsilon:
                a = random.choice(env.actions)
            else:
                max_q = max(q[s][a] for a in env.actions)
                actions_with_max = [a for a in env.actions if q[s][a] == max_q]
                a = random.choice(actions_with_max)
            
            # Sample next state according to transition probabilities
            s2, prob = random.choices(env.transition(s, a), weights=[p[1] for p in env.transition(s, a)], k=1)[0]
            
            # Get reward for entering s2
            r = env.get_reward(s2)
            
            # Compute target
            if env.is_terminal(s2):
                target = r
            else:
                max_next_q = max(q[s2][a2] for a2 in env.actions)
                target = r + env.gamma * max_next_q
            
            # Update Q value
            q[s][a] += alpha * (target - q[s][a])
            
            s = s2
        
        if env.is_terminal(s):
            break
    
    # Compute policy: for each non-terminal state, pick action with highest Q
    policy = {}
    for s in env.all_states():
        if not env.is_terminal(s):
            max_q = max(q[s][a] for a in env.actions)
            actions_with_max = [a for a in env.actions if q[s][a] == max_q]
            policy[s] = random.choice(actions_with_max)
        else:
            policy[s] = None
    
    return q, policy

if __name__ == "__main__":
    pass
