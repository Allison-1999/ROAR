from ROAR.configurations.configuration import Configuration as AgentConfig
from ROAR.control_module.pid_controller import PIDController#TO REMOVE
from ROAR.planning_module.local_planner.loop_simple_waypoint_following_local_planner import \
    LoopSimpleWaypointFollowingLocalPlanner#TO REMOVE
from ROAR.planning_module.behavior_planner.behavior_planner import BehaviorPlanner#TO REMOVE
from ROAR.planning_module.mission_planner.waypoint_following_mission_planner import WaypointFollowingMissionPlanner
from pathlib import Path
from ROAR.utilities_module.occupancy_map import OccupancyGridMap
from ROAR.perception_module.obstacle_from_depth import ObstacleFromDepth
from ROAR.agent_module.agent import Agent
from ROAR.utilities_module.data_structures_models import ViveTrackerData
from ROAR.utilities_module.vehicle_models import Vehicle, VehicleControl
import numpy as np
from ROAR.utilities_module.data_structures_models import Transform, Location
import cv2
from typing import Optional
import scipy.stats

class RLe2ePPOAgent(Agent):
    def __init__(self, vehicle: Vehicle, agent_settings: AgentConfig, **kwargs):
        super().__init__(vehicle, agent_settings, **kwargs)
        # self.route_file_path = Path(self.agent_settings.waypoint_file_path)#TO REMOVE
        # self.pid_controller = PIDController(agent=self, steering_boundary=(-1, 1), throttle_boundary=(0, 1))#TO REMOVE
        self.mission_planner = WaypointFollowingMissionPlanner(agent=self)
        # # initiated right after mission plan#TO REMOVE
        # self.behavior_planner = BehaviorPlanner(agent=self)#TO REMOVE
        # self.local_planner = LoopSimpleWaypointFollowingLocalPlanner(#TO REMOVE
        #     agent=self,
        #     controller=self.pid_controller,
        #     mission_planner=self.mission_planner,
        #     behavior_planner=self.behavior_planner,
        #     closeness_threshold=1.5
        # )#TO REMOVE

        # the part about visualization
        self.occupancy_map = OccupancyGridMap(agent=self, threaded=True)

        occ_file_path = Path("../ROAR_Sim/data/berkeley_minor_cleaned_global_occu_map.npy")
        self.occupancy_map.load_from_file(occ_file_path)

        self.plan_lst = list(self.mission_planner.produce_single_lap_mission_plan())

        self.kwargs = kwargs
        self.interval = self.kwargs.get('interval', 150)
        self.look_back = self.kwargs.get('look_back', 5)
        self.look_back_max = self.kwargs.get('look_back_max', 10)
        self.thres = self.kwargs.get('thres', 1e-3)

        self.int_counter = 0
        self.cross_reward=0
        self.counter = 0
        self.finished = False
        self.curr_dist_to_strip = 0
        self.bbox: Optional[LineBBox] = None
        self.bbox_list = []# list of bbox
        self._get_next_bbox()

    def run_step(self, sensors_data: ViveTrackerData, vehicle: Vehicle) -> VehicleControl:
        super(RLe2ePPOAgent, self).run_step(sensors_data, vehicle)
        #print(self.vehicle.transform)
        #self.local_planner.run_in_series()#TO REMOVE

        self.curr_dist_to_strip = self.bbox_step()
        if self.kwargs.get("control") is None:
            return VehicleControl()
        else:
            return self.kwargs.get("control")

    def bbox_step(self):
        """
        This is the function that the line detection agent used
        Main function to use for detecting whether the vehicle reached a new strip in
        the current step. The old strip (represented as a bbox) will be gone forever
        return:
        crossed: a boolean value indicating whether a new strip is reached
        dist (optional): distance to the strip, value no specific meaning
        """
        self.counter += 1
        if not self.finished:
            while(True):
                crossed, dist = self.bbox.has_crossed(self.vehicle.transform)
                if crossed:
                    self.int_counter += 1
                    self.cross_reward+=crossed
                    self._get_next_bbox()
                else:
                    break

            return dist
        return False, 0.0

    def _get_next_bbox(self):
        # make sure no index out of bound error
        curr_lb = self.look_back
        curr_idx = self.int_counter * self.interval
        while curr_idx + curr_lb < len(self.plan_lst):
            if curr_lb > self.look_back_max:
                self.int_counter += 1
                curr_lb = self.look_back
                curr_idx = self.int_counter * self.interval
                continue

            t1 = self.plan_lst[curr_idx]
            t2 = self.plan_lst[curr_idx + curr_lb]

            dx = t2.location.x - t1.location.x
            dz = t2.location.z - t1.location.z
            if abs(dx) < self.thres and abs(dz) < self.thres:
                curr_lb += 1
            else:
                self.bbox = LineBBox(t1, t2)
                return
        # no next bbox
        print("finished all the iterations!")
        self.finished = True

    def _get_bbox_list(self, num):
        # make sure no index out of bound error
        self.bbox_list = []#clear bbox_list
        curr_lb = self.look_back
        curr_idx = self.int_counter * self.interval
        while curr_idx + curr_lb < len(self.plan_lst):
            if curr_lb > self.look_back_max:
                self.int_counter += 1
                curr_lb = self.look_back
                curr_idx = self.int_counter * self.interval
                continue

            t1 = self.plan_lst[curr_idx]
            t2 = self.plan_lst[curr_idx + curr_lb]

            dx = t2.location.x - t1.location.x
            dz = t2.location.z - t1.location.z
            if abs(dx) < self.thres and abs(dz) < self.thres:
                curr_lb += 1
            else:
                if num > 0:
                    num -= 1
                    self.bbox_list.append(LineBBox(t1, t2))
                    curr_lb = self.look_back #update curr_lb
                    curr_idx = self.int_counter * self.interval
                else:
                    return

        # no next bbox
        print("finished all the iterations!")
        self.finished = True


class LineBBox(object):
    def __init__(self, transform1: Transform, transform2: Transform) -> None:
        self.x1, self.z1 = transform1.location.x, transform1.location.z
        self.x2, self.z2 = transform2.location.x, transform2.location.z
        #print(self.x2, self.z2)
        self.pos_true = True
        self.thres = 1e-2
        self.eq = self._construct_eq()
        self.dis = self._construct_dis()
        self.strip_list = None
        self.size=20

        if self.eq(self.x1, self.z1) > 0:
            self.pos_true = False

    def _construct_eq(self):
        dz, dx = self.z2 - self.z1, self.x2 - self.x1

        if abs(dz) < self.thres:
            def vertical_eq(x, z):
                return x - self.x2

            return vertical_eq
        elif abs(dx) < self.thres:
            def horizontal_eq(x, z):
                return z - self.z2

            return horizontal_eq

        slope_ = dz / dx
        self.slope = -1 / slope_
        # print("tilted strip with slope {}".format(self.slope))
        self.intercept = -(self.slope * self.x2) + self.z2

        def linear_eq(x, z):
            return z - self.slope * x - self.intercept

        return linear_eq

    def _construct_dis(self):
        dz, dx = self.z2 - self.z1, self.x2 - self.x1

        if abs(dz) < self.thres:
            def vertical_dis(x, z):
                return z - self.z2

            return vertical_dis
        elif abs(dx) < self.thres:
            def horizontal_dis(x, z):
                return x - self.x2

            return horizontal_dis

        slope_ = dz / dx
        self.slope = -1 / slope_
        # print("tilted strip with slope {}".format(self.slope))
        self.intercept = -(self.slope * self.x2) + self.z2

        def linear_dis(x, z):
            z_diff=z - self.z2
            x_diff=x - self.x2
            dis=np.sqrt(np.square(z_diff)+np.square(x_diff))
            angle1=np.abs(np.arctan(slope_))
            angle2=np.abs(np.arctan(z_diff/x_diff))
            return dis*np.sin(np.abs(angle2-angle1))

        return linear_dis

    def has_crossed(self, transform: Transform):
        x, z = transform.location.x, transform.location.z
        dist = self.eq(x, z)
        crossed=dist > 0 if self.pos_true else dist < 0
        middle=scipy.stats.norm(self.size//2, self.size//2).pdf(self.size//2)
        return (scipy.stats.norm(self.size//2, self.size//2).pdf(self.size//2-self.dis(x, z))/middle if crossed else 0, dist)

    def get_visualize_locs(self, size=10):
        if self.strip_list is not None:
            return self.strip_list

        name = self.eq.__name__
        if name == 'vertical_eq':
            xs = np.repeat(self.x2, size)
            zs = np.arange(self.z2 - (size // 2), self.z2 + (size // 2))
        elif name == 'horizontal_eq':
            xs = np.arange(self.x2 - (size // 2), self.x2 + (size // 2))
            zs = np.repeat(self.z2, size)
        else:
            range_ = size * np.cos(np.arctan(self.slope))
            xs = np.linspace(self.x2 - range_ / 2, self.x2 + range_ / 2, num=size)
            zs = self.slope * xs + self.intercept
            # print(np.vstack((xs, zs)).T)

        #         self.strip_list = np.vstack((xs, zs)).T
        self.strip_list = []
        for i in range(len(xs)):
            self.strip_list.append(Location(x=xs[i], y=0, z=zs[i]))
        return self.strip_list

    def get_value(self,size=10):
        middle=scipy.stats.norm(size//2, size//2).pdf(size//2)
        return [scipy.stats.norm(size//2, size//2).pdf(i)/middle*0.5 for i in  range(size)]

    def get_directional_velocity(self,x,y):
        dz, dx = self.z2 - self.z1, self.x2 - self.x1
        dx,dz=[dx,dz]/np.linalg.norm([dx,dz])
        return dx*x+dz*y

    def to_array(self,x,z):
        dz, dx = self.z2 - self.z1, self.x2 - self.x1
        slope_ = dz / (dx+1e-30)
        angle1=np.arctan(slope_)/np.pi*2

        dz, dx = self.z2 - z, self.x2 - x
        slope_ = dz / (dx+1e-30)
        angle2=np.arctan(slope_)/np.pi*2
        return np.array([self.x2 , self.z2,angle1,angle2])

    def get_yaw(self):
        dz, dx = self.z2 - self.z1, self.x2 - self.x1
        # slope_ = dz / (dx+1e-30)
        if dz<0.01:
            angle=90
        else:
            slop=dx/dz
            angle=np.arctan(slop)/np.pi*180
        print(angle)
        return angle
