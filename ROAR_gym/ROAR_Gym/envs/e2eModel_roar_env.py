try:
    from ROAR_Gym.envs.roar_env import ROAREnv
except:
    from ROAR_Gym.ROAR_Gym.envs.roar_env import ROAREnv

from ROAR.utilities_module.vehicle_models import VehicleControl
from ROAR.agent_module.agent import Agent
from ROAR.utilities_module.vehicle_models import Vehicle
from typing import Tuple
import numpy as np
from typing import List, Any
import gym
import math
from collections import OrderedDict
from gym.spaces import Discrete, Box
import cv2

# Define the discrete action space
# DISCRETE_ACTIONS = {
#     0: [0.0, 0.0],  # Coast
#     1: [0.0, -0.5],  # Turn Left
#     2: [0.0, 0.5],  # Turn Right
#     3: [1.0, 0.0],  # Forward
#     4: [-0.5, 0.0],  # Brake
#     5: [1.0, -0.5],  # Bear Left & accelerate
#     6: [1.0, 0.5],  # Bear Right & accelerate
#     7: [-0.5, -0.5],  # Bear Left & decelerate
#     8: [-0.5, 0.5],  # Bear Right & decelerate
# }
# DISCRETE_ACTIONS = {
#     0: [0.5, 0.0, 0.0],  # Coast
#     1: [0.5, -0.5, 0.0],  # Turn Left
#     2: [0.5, 0.5, 0.0],  # Turn Right
#     3: [0.5, 0.0, 0.0],  # Forward
#     4: [0.5, 0.0, 0.0],  # Brake
#     5: [0.5, -0.5, 0.0],  # Bear Left & accelerate
#     6: [0.5, 0.5, 0.0],  # Bear Right & accelerate
#     7: [0.5, -0.5, 0.0],  # Bear Left & decelerate
#     8: [0.5, 0.5, 0.0],  # Bear Right & decelerate
# }
mode='no_map'
if mode=='no_map':
    FRAME_STACK = 1
else:
    FRAME_STACK = 4
CONFIG = {
    #max values are 280x280
    #original values are 80x80
    "x_res": 80,
    "y_res": 80
}


class ROARppoEnvE2E(ROAREnv):
    def __init__(self, params):
        super().__init__(params)
        #self.action_space = Discrete(len(DISCRETE_ACTIONS))
        low=np.array([0.0, -1.0, 0.0])
        high=np.array([1.0, 1.0, 1.0])
        self.action_space = Box(low=np.tile(low,(FRAME_STACK)), high=np.tile(high,(FRAME_STACK)), dtype=np.float32)
        self.mode=mode
        if self.mode=='no_map':
            self.observation_space = Box(low=np.tile([-1],(14)), high=np.tile([1],(14)), dtype=np.float32)
        else:
            self.observation_space = Box(-1, 1, shape=(FRAME_STACK, CONFIG["x_res"], CONFIG["y_res"]), dtype=np.float32)
        self.prev_speed = 0
        self.prev_cross_reward = 0
        self.crash_check = False
        self.ep_rewards = 0
        self.frame_reward = 0
        self.highscore = -1000
        self.highest_chkpt = 0
        self.speeds = []
        self.prev_int_counter = 0

    def step(self, action: Any) -> Tuple[Any, float, bool, dict]:
        obs = []
        rewards = []

        for i in range(FRAME_STACK):
            throttle=np.sqrt(action[i*3+0])
            steering=np.sign(action[i*3+1])*np.max([np.square(action[i*3+1])-0.5,0])
            braking=np.max([np.square(action[i*3+2])-0.9,0])
            self.agent.kwargs["control"] = VehicleControl(throttle=throttle,
                                                          steering=steering,
                                                          braking=braking)
            ob, reward, is_done, info = super(ROARppoEnvE2E, self).step(action)
            obs.append(ob)
            rewards.append(reward)
            if is_done:
                break
        self.render()
        self.frame_reward = sum(rewards)
        self.ep_rewards += sum(rewards)
        if is_done:
            self.crash_check = False
            self.update_highscore()
            self.ep_rewards = 0
        return np.array(obs), self.frame_reward, self._terminal(), self._get_info(action)

    def _get_info(self, action: Any) -> dict:
        info_dict = OrderedDict()
        info_dict["Current HIGHSCORE"] = self.highscore
        info_dict["Furthest Checkpoint"] = self.highest_chkpt
        info_dict["episode reward"] = self.ep_rewards
        info_dict["checkpoints"] = self.agent.int_counter
        info_dict["reward"] = self.frame_reward
        # info_dict["throttle"] = action[0]
        # info_dict["steering"] = action[1]
        # info_dict["braking"] = action[2]
        return info_dict

    def update_highscore(self):
        if self.ep_rewards > self.highscore:
            self.highscore = self.ep_rewards
        if self.agent.int_counter > self.highest_chkpt:
            self.highest_chkpt = self.agent.int_counter
        self.ep_rewards = 0
        return

    def _terminal(self) -> bool:
        if self.carla_runner.get_num_collision() > self.max_collision_allowed:
            return True
        else:
            return False

    def get_reward(self) -> float:
        # prep for reward computation
        reward = -0.4*(1-self.agent.vehicle.control.throttle+100*self.agent.vehicle.control.braking+abs(self.agent.vehicle.control.steering))
        curr_dist_to_strip = self.agent.curr_dist_to_strip

        if self.crash_check:
            return reward
        # reward computation
        current_speed = self.agent.bbox.get_directional_velocity(self.agent.vehicle.velocity.x,self.agent.vehicle.velocity.z)
        self.speeds.append(current_speed)

        if self.agent.cross_reward > self.prev_cross_reward:
            num_crossed = self.agent.int_counter - self.prev_int_counter
            #speed reward
            reward+= np.average(self.speeds) * num_crossed*5
            self.speeds=[]
            self.prev_int_counter =self.agent.int_counter
            #crossing reward
            reward += 20 * (self.agent.cross_reward - self.prev_cross_reward)

        if self.carla_runner.get_num_collision() > 0:
            reward -= 100#0 /(min(total_num_cross,10))
            self.crash_check = True

        # log prev info for next reward computation
        self.prev_speed = Vehicle.get_speed(self.agent.vehicle)
        self.prev_cross_reward = self.agent.cross_reward
        return reward

    def _get_obs(self) -> np.ndarray:
        # star edited this: it's better to set the view_size directly instead of doing resize
        if self.mode=='no_map':
            vehicle_state=self.agent.vehicle.to_array() #11
            vehicle_state[[0,1,2]]/=140
            vehicle_state[[3,4,5]]/=3080
            vehicle_state[[6,7,8]]/=180
            line_location=self.agent.bbox.to_array() #3
            line_location[[0,1]]/=3080
            line_location[[0,1]]-=vehicle_state[[3,5]]
            data=np.concatenate([vehicle_state,line_location])

            img = self.agent.occupancy_map.get_map(transform=self.agent.vehicle.transform,
                                                    view_size=(CONFIG["x_res"], CONFIG["y_res"]),
                                                    arbitrary_locations=self.agent.bbox.get_visualize_locs(size=20),
                                                    arbitrary_point_value=self.agent.bbox.get_value(size=20)
                                                    )
            # data = cv2.resize(occu_map, (CONFIG["x_res"], CONFIG["y_res"]), interpolation=cv2.INTER_AREA)
            #cv2.imshow("Occupancy Grid Map", cv2.resize(np.float32(data), dsize=(500, 500)))

            img_view=np.sum(img,axis=2)
            cv2.imshow("data", img_view) # uncomment to show occu map
            cv2.waitKey(1)

            return data
        else:
            data = self.agent.occupancy_map.get_map(transform=self.agent.vehicle.transform,
                                                    view_size=(CONFIG["x_res"], CONFIG["y_res"]),
                                                    arbitrary_locations=self.agent.bbox.get_visualize_locs(size=20),
                                                    arbitrary_point_value=self.agent.bbox.get_value(size=20)
                                                    )
            # data = cv2.resize(occu_map, (CONFIG["x_res"], CONFIG["y_res"]), interpolation=cv2.INTER_AREA)
            #cv2.imshow("Occupancy Grid Map", cv2.resize(np.float32(data), dsize=(500, 500)))

            data_view=np.sum(data,axis=2)
            cv2.imshow("data", data_view) # uncomment to show occu map
            cv2.waitKey(1)
            # yaw_angle=self.agent.vehicle.transform.rotation.yaw
            velocity=self.agent.vehicle.get_speed(self.agent.vehicle)
            data[0,0,2]=velocity

            return data_view  # height x width x 3 array
    #3location 3 rotation 3velocity 20 waypoline locations 20 wayline rewards

    def reset(self) -> Any:
        super(ROARppoEnvE2E, self).reset()
        return self._get_obs()