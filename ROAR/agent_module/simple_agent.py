from ROAR.agent_module.agent import Agent
from ROAR.utilities_module.data_structures_models import SensorsData
from ROAR.utilities_module.vehicle_models import Vehicle, VehicleControl
from ROAR.configurations.configuration import Configuration as AgentConfig

class SimpleAgent(object):
    def __init__(self, agent_settings: AgentConfig):
        self.agent_settings = AgentConfig
        self.action_dict = {}

    def run_step(self, obs):
        """ Returns `action_dict` containing actions for each agent in the env
        """
        for name in self.npc_config.keys():
            # ... Process obs of each agent and generate action ...
            self.action_dict[name] = [1, 0]  # Full-throttle
        return self.action_dict
