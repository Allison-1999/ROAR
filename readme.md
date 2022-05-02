# Robot Open Autonomous Racing (ROAR) - Multi-Agent Support
The existing code base and API of the CARLA simulator and the OpenAI Gym third party environment developed for the ROAR project mainly focuses on the interaction between one vehicle and the environment. However, in fact, one agent not only interacts with the environment but also interaction with other agents exists in the same environment in the realistic situation.

In this project, a new Gym-CARLA environment, ROARMultiEnv, has been developed to support multi-agent autonomous driving simulation. It is based on CARLA API and uses Ray Library. A simple_agent was developed for testing.

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
- Blueprint:Blueprint is the specific attributes definition of an actor. New actors initialized through a blueprint. 
- World: The world is the major ruler of the simulation. It represents the currently loaded map, and contains the setting of parameters of the current simulation environment and functions that create, control and destroy actors. CARLA provides carla.World as the default world setting. 

### Result
![img](https://lh4.googleusercontent.com/LZ8KGJXVh-fIpk_php4efI__S979uRv423DiCZAv0cTjUXcI04QXbnciYfuGGCGuMVjPR8OWq8Pniw9in-u-FsTym6eoOYGY5yDZfiqkg98BaTtz3Iie3Wiucct7eF3OzJJyhdbl)

### Future Work
- Develop environment subclasses based on ROARMultiEnv to support more different types of agents in the ROAR project, such as rl_e2e_ppo_agent, and etc.
- The process of executing the step for each agent can be parallelized
