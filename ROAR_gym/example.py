import os
import sys
from pathlib import Path

sys.path.append(Path(os.getcwd()).parent.as_posix())
import gym
import ROAR_Gym
from ROAR_Sim.configurations.configuration import Configuration as CarlaConfig
from ROAR.configurations.configuration import Configuration as AgentConfig
from ROAR.agent_module.agent import Agent
from ROAR.agent_module.pid_agent import PIDAgent
from ROAR.agent_module.simple_agent import SimpleAgent

def main():
    # Set gym-carla environment
    agent_config = AgentConfig.parse_file(Path("configurations/agent_configuration.json"))
    carla_config = CarlaConfig.parse_file(Path("configurations/carla_configuration.json"))

    # from gym import envs
    # print(envs.registry.all())

    params = {
        "agent_config": agent_config,
        "carla_config": carla_config,
        "ego_agent_class": PIDAgent,
        "npc_agent_class": SimpleAgent
    }
    env = gym.make('roar-multi-v0', params=params)
    for ep in range(2):
        obs: obs = env.reset()
        done = {"__all__": False}
        step = 0
        while not done["__all__"]:
            reward,terminal = env.step([1,0])
            print(f"Step#:{step}  Rew:{reward}  Done:{done}")
            step += 1
        env.close()


if __name__ == '__main__':
    main()