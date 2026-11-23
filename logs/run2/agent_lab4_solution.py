import random

def q_learning(env, n_episodes, alpha, epsilon):
    # Initialize Q table with zeros for all states and actions
    q = {}
    for s in env.all_states():
        q[s] = {a: 0.0 for a in env.actions}
    
    episodes_run = 0
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
            
            # Sample next state from transition probabilities
            s2, prob = random.choice(env.transition(s, a))
            
            # Get reward for entering s2
            r = env.get_reward(s2)
            
            # Determine target value
            if env.is_terminal(s2):
                target = r
            else:
                max_next_q = max(q[s2][a2] for a2 in env.actions)
                target = r + env.gamma * max_next_q
            
            # Q-learning update
            q[s][a] = q[s][a] + alpha * (target - q[s][a])
            
            s = s2
        
        episodes_run += 1
    
    # Derive policy from Q table
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
    pass
