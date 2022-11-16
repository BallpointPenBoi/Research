import envs.battle_env as battle_env
import maddpg.team as maddpg
import instinct.team as instinct
import numpy as np
from pprint import pprint
import os
import datetime
from utils.utils import plot_data
import sys

def merge_dicts(dict1, dict2):
    dict2.update(dict1)
    return dict2

GAMMA = 0.95
LEARNING_RATE = 0.01
BUFFER_SIZE = 100_000
BATCH_SIZE = 1_024
PRINT_INTERVAL = 100
SAVE_INTERVAL = 100
LEARN_INTERVAL = 10
SHOW_INTERVAL = 1_000
N_GAMES = 500_000

env_config = {
    'n_agents': 2, # Number of planes on each team
    'show': False, # Show visuals
    'hit_base_reward': 50, # Reward value for hitting enemy base
    'hit_plane_reward': 25, # Reward value for hitting enemy plane
    'miss_punishment': -1, # Punishment value for missing a shot
    'die_punishment': 0, # Punishment value for a plane dying
    'lose_punishment': -30, # Punishment for losing the game (The goal is to possibly defend the base)
    'fps': 30, # Framerate that the visuals run at
    'continuous_actions': True
}

def main():
    # Create a new folder for the model
    for i in range(1, 100):
        if not os.path.exists(f'models/maddpg_{i}'):
            FOLDER = f'models/maddpg_{i}'
            os.makedirs(FOLDER)
            os.makedirs(f'{FOLDER}/training_vids')
            break

    hyperparams = {
        "gamma":GAMMA,
        "learning_rate":LEARNING_RATE,
        "buffer_size":BUFFER_SIZE,
        "batch_size":BATCH_SIZE,
        "n_games":N_GAMES
    }

    with open(f"{FOLDER}/config.txt", 'a') as f:
        f.write("MADDPG\n\nENV CONFIG:\n")
        pprint(env_config, stream=f)
        f.write("\nHYPERPARAMETERS:\n")
        pprint(hyperparams, stream=f)
        
    env = battle_env.parallel_env(**env_config)
    red_agent_list = env.possible_red
    blue_agent_list = env.possible_blue
    obs_len = env.observation_space(red_agent_list[0]).shape[0]
    critic_dims = obs_len * env.n_agents
    red_team = maddpg.Team(red_agent_list, obs_len, env.n_actions, critic_dims, chkpt_dir=FOLDER, mem_size=BUFFER_SIZE, batch_size=BATCH_SIZE, lr=LEARNING_RATE)
    blue_team = instinct.Team(blue_agent_list, red_agent_list, env)


    steps = 0
    red_scores = []
    blue_scores = []

    print(f'\n{" Starting Training ":=^43}')
    start = datetime.datetime.now()

    for i in range(N_GAMES+1):
        sys.stdout.write(f"\r{' Episode {game}, %{percent:.2f} Complete '.format(game = i, percent = i / N_GAMES * 100):=^43}")
        # Episode {i}, %{i / N_GAMES * 100:.2f} Complete
        observations = env.reset()

        red_score = 0
        blue_score = 0
        red_obs = {}
        blue_obs = {}

        for agent in red_agent_list:
            red_obs[agent] = observations[agent]
        for agent in blue_agent_list:
            blue_obs[agent] = observations[agent]

        if i % SHOW_INTERVAL == 0:
            env.show = True
            env.start_recording(f'{FOLDER}/training_vids/{i}.mp4')

        elif env.show == True:
            env.export_video()
            env.show = False
            env.close()

        while not env.env_done:
            actions = merge_dicts(red_team.choose_actions(red_obs), blue_team.choose_actions(blue_obs))

            observations_, rewards, dones, _ = env.step(actions)

            red_obs_ = {}
            red_actions = {}
            red_rewards = {}
            red_dones = {}
            blue_obs_ = {}
            blue_actions = {}
            blue_rewards = {}
            blue_dones = {}

            for agent in red_agent_list:
                red_obs_[agent] = observations_[agent]
                red_actions[agent] = actions[agent]
                red_rewards[agent] = rewards[agent]
                red_score += rewards[agent]
                red_dones[agent] = dones[agent]

            for agent in blue_agent_list:
                blue_obs_[agent] = observations_[agent]
                blue_score += rewards[agent]

            red_team.memory.store_transition(red_obs, red_actions, red_rewards, red_obs_, red_dones)

            if steps % LEARN_INTERVAL == 0 and steps > 0:
                red_team.learn()

            if steps % SAVE_INTERVAL == 0 and steps > 0:
                red_team.save_models()

            red_obs = red_obs_
            blue_obs = blue_obs_

            red_scores.append(red_score)
            blue_scores.append(blue_score)
            steps += 1

        if i % PRINT_INTERVAL == 0 and i > 0:
            now = datetime.datetime.now()
            elapsed = now - start
            s = elapsed.total_seconds()
            hours, remainder = divmod(s, 3600)
            minutes, seconds = divmod(remainder, 60)
            formatted_elapsed = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            formatted_time = f"{now.hour}:{now.minute}:{now.second}"
            avg_red = np.mean(red_scores[-PRINT_INTERVAL:])
            avg_blue = np.mean(blue_scores[-PRINT_INTERVAL:])
            statement = (
                f"\n{'-'*43}\n"
                f"| {('Current Time: ' + str(formatted_time)):<40}|\n"
                f"| {('Elapsed Time: ' + str(formatted_elapsed)):<40}|\n"
                f"| {('Games: ' + str(i)):<40}|\n"
                f"| {('Timesteps: ' + str(steps)):<40}|\n"
                f"| {('Red Avg Score: ' + str(avg_red)):<40}|\n"
                f"| {('Blue Avg Score: ' + str(avg_blue)):<40}|\n"
                f"{'-'*43}\n"
            )
            print(statement)
            
    score_dict = {
        "red": red_scores,
        "blue": blue_scores
    }

    plot_data(score_dict, FOLDER + '/scores.svg')

if __name__ == '__main__':
    main()