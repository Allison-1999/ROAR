# Robot Open Autonomous Racing (ROAR) - Multi-Agent Support
The existing code base and API of the CARLA simulator and the OpenAI Gym third party environment developed for the ROAR project mainly focuses on the interaction between one vehicle and the environment. However, in fact, one agent not only interacts with the environment but also interaction with other agents exists in the same environment in the realistic situation.

In this project, a new Gym-CARLA environment, ROARMultiEnv, has been developed to support multi-agent autonomous driving simulation. It is based on CARLA API and uses Ray Library. A simple_agent was developed for testing.


Other things for readme:
1. stable_baseline3 modification
2. requirements installation  -->  regenerate one.
```
git clone https://github.com/Allison-1999/ROAR.git ROAR1
git clone https://github.com/Allison-1999/ROAR.git ROAR2

Build environment and install packages

Open your PyCharm USING `RUN AS ADMINISTRATION` (Otherwise, the model saving will fail)
And open the ROAR1 and ROAR2 projects in two PyCharm windows

After installing the packages, to run e2eModel, please change the stable_baseline3.
You can choose to enter the `\.conda\envs\ROAR\Lib\site-packages` directory, delete the `stable_baselines3-1.5.0.dist-info` and `stable_baselines3` folders and then copy the two folders with the same names under `ROAR\package_stable_baselines3` to `\.conda\envs\ROAR\Lib\site-packages` directory instead.
Otherwise, you can edit the package manually by checking the instruction on the top section of `ROAR_gym/e2eModel.py`, which was written by the group member who is responsible for RL model training.

change spawn_point_id in ROAR_gym/configurations/agent_configuration.json line 60, set 0 for ROAR1 and set 1 for ROAR2
with its context should be:

for ROAR1:
    "enable_autopilot": true,
    "spawn_point_id": 0,
    "show_sensors_data": true,
    "save_sensor_data": false

for ROAR2:
    "enable_autopilot": true,
    "spawn_point_id": 1,
    "show_sensors_data": true,
    "save_sensor_data": false
    
    [NOTICE] In the Berkeley minor map, the spawn points are too close to each other. 
    So even when you set different spawn points, you may still get the `ValueError: Cannot spawn actor at ID [1]. Error: Spawn failed because of collision at spawn position`\
    In that case, please make sure you start one client first, and start the second client a few second later.
    
    In this case, you may also need to restart the UE4 engine, since the vehicle from a previous failure client may still remain in the simulation world and hold the spawn point.
    
also change the `"run_name"` in the following file: ROAR_gym/configurations/ppo_configuration.py
for ROAR1:
misc_params = {
  "env_name": 'roar-e2e-ppo-v0',
  "run_fps": 8,  # TODO Link to the environment RUN_FPS
  "model_directory": Path("./output/PPOe2e_Run_1"),
  "run_name": "ROAR1",
  "total_timesteps": int(1e6),
}

for ROAR2:
misc_params = {
  "env_name": 'roar-e2e-ppo-v0',
  "run_fps": 8,  # TODO Link to the environment RUN_FPS
  "model_directory": Path("./output/PPOe2e_Run_1"),
  "run_name": "ROAR2",
  "total_timesteps": int(1e6),
}

if you got the following error, please change the `"run_name"` to a new string that never been used, for instance, you can append your nickname to it.
wandb: Currently logged in as: jingjingwei. Use `wandb login --relogin` to force relogin
wandb: ERROR Error while calling W&B API: Error 1062: Duplicate entry '908467-Run 1' for key 'PRIMARY' (<Response [409]>)



then, change the ROAR_gym/configurations/wandb_configuration.json file, set different run id. Set 1 for ROAR1, and set 2 for ROAR 2
for ROAR1:
{"run_id": "ROAR1, "name": "", "project_name": "ROAR", "entity": "jingjingwei"}
for ROAR2:
{"run_id": "ROAR2", "name": "", "project_name": "ROAR", "entity": "jingjingwei"}


then, set the API key for wandb
(login and input the API key)

https://docs.wandb.ai/quickstart
`pip install wandb`
`wandb login a20e04de52982c4c0293909e28070b1338acba5e`
```


### New Dependency
```
pip install -U ray
```
```
pip install -U "ray[rllib]" 
```
```
pip install redis
```

### Quick start
```
python runner_multi_agent.py
```
#### npc config path
ROAR/ROAR_Sim/configurations/npc_config.json
### Some Concept
CARLA provides support for multi-agent through the following three core concepts.
- Actor: Actor is anything that participates in the simulation and can be moved around, for example, vehicles, pedestrians.
- Blueprint: Blueprint is the specific attributes definition of an actor. New actors initialized through a blueprint. 
- World: The world is the major ruler of the simulation. It represents the currently loaded map, and contains the setting of parameters of the current simulation environment and functions that create, control and destroy actors. CARLA provides carla.World as the default world setting. 

### Result
![img](https://lh4.googleusercontent.com/LZ8KGJXVh-fIpk_php4efI__S979uRv423DiCZAv0cTjUXcI04QXbnciYfuGGCGuMVjPR8OWq8Pniw9in-u-FsTym6eoOYGY5yDZfiqkg98BaTtz3Iie3Wiucct7eF3OzJJyhdbl)

### Future Work
- Develop environment subclasses based on ROARMultiEnv to support more different types of agents in the ROAR project, such as rl_e2e_ppo_agent, and etc.
- The process of executing the step for each agent can be parallelized

### Reference
[1]M. Zhou, J. Luo, J. Villella, Y. Yang, D. Rusu, J. Miao, W. Zhang, M. Alban, I. Fadakar, Z. Chen, et al. SMARTS: Scalable Multi-Agent Reinforcement Learning Training School for Autonomous Driving. arXiv preprint arXiv:2010.09776, 2020

[2]P. Moritz, R. Nishihara, S. Wang, A. Tumanov, R. Liaw, E. Liang, M. Elibol, Z. Yang, W. Paul, M. I. Jordan, et al. Ray: A distributed framework for emerging AI applications. In OSDI, pages 561–577, 2018.

[3]P. Palanisamy, “Multi-agent connected autonomous driving using Deep Reinforcement Learning,” 2020 International Joint Conference on Neural Networks (IJCNN), 2020. 

