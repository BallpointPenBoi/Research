import supersuit as ss
from stable_baselines3 import PPO
import battle_v1

cf = {
    'n_agents': 3, # Number of planes on each team
    'show': False, # Show visuals
    'hit_base_reward': 10, # Reward value for hitting enemy base
    'hit_plane_reward': 2, # Reward value for hitting enemy plane
    'miss_punishment': 0, # Punishment value for missing a shot
    'lose_punishment': -10, # Punishment value for losing the game
    'die_punishment': -1, # Punishment value for a plane dying
    'fps': 15 # Framerate that the visuals run at
}

env = battle_v1.parallel_env(**cf)
env = ss.black_death_v3(env)
env = ss.pettingzoo_env_to_vec_env_v1(env)
env = ss.concat_vec_envs_v1(env, 1, num_cpus=1, base_class="stable_baselines3")
model = PPO(
    'MlpPolicy',
    env,
    verbose=1,
)
model.learn(total_timesteps=100000)
model.save("policy")

env = battle_v1.env(**cf)
model = PPO.load("policy")

env.reset()
for agent in env.agent_iter():
    obs, reward, done, info = env.last()
    act = model.predict(obs, deterministic=True)[0] if not done else None
    env.step(act)
    env.render()