"""
Code for generating demo occupancy map from given points
author: Xinchi Huang
"""

import math
import numpy as np
import cv2
from gabreil_graph import is_valid_point,global_to_local

class MapSimulator:
    def __init__(
        self,
        robot_size=0.15,
        max_height=0.3,
        map_size=100,
        max_x=5,
        max_y=5,
        sensor_view_angle=2*math.pi,
        local=True,
        block=True,
        partial=False,
        position_encoding=False
    ):
        """
        :param robot_size: Size of robot in occupancy map
        :param max_height: points' horizontal range
        :param map_size: The size of occupancy map
        :param max_x: Max world x coordinate
        :param max_y: Max world y coordinate
        :param local: Control whether to rotate the occupancy map or not(True: local map, False: global map)
        :param block: Control whether to consider the blocking conditions
        :param partial: partially observed or fully observed
        """

        self.robot_size = robot_size
        self.max_height = max_height
        self.map_size = map_size
        self.max_x = max_x
        self.max_y = max_y
        self.sensor_view_angle=sensor_view_angle
        self.local = local
        self.block = block
        self.partial = partial
        self.position_encoding=position_encoding
        if self.position_encoding==True:
            self.position_encoding_matrix=np.ones((self.map_size,self.map_size))
            for i in range(self.map_size):
                for j in range(self.map_size):
                    if i==self.map_size/2 and j==self.map_size/2:
                        self.position_encoding_matrix[i][j]=1
                        continue
                    self.position_encoding_matrix[i][j]=1/max(abs(i-self.map_size/2),abs(j-self.map_size/2))
        print("MapSimulator",self.__dict__)

    def world_to_map(self, world_point, map_size, max_x, max_y):
        """
        Transform points from world coordinate to map coordinate
        :param world_point: points' world coordinate
        :param map_size: The size of occupancy map
        :param max_x: Max world x coordinate
        :param max_y: Max world y coordinate
        :return: points in map coordinate

        """
        # if world_point == None:
        #     return None
        x_world = world_point[0]
        y_world = world_point[1]


        # x_map = int((max_x - x_world) / (2 * max_x) * map_size)
        # y_map = int((max_y + x_world) / (2 * max_y) * map_size)

        y_map = min(int(map_size/2)+int(x_world*map_size/max_x/2), map_size-1)
        x_map = min(int(map_size/2)-int(y_world*map_size/max_y/2), map_size-1)
        if 0 <= x_map < map_size and 0 <= y_map < map_size:
            return [x_map, y_map]
        return None

    def generate_map_all(
        self,
        position_list_local,
    ):

        """
        Generate occupancy map with fully observed
        :param position_list_local: All robots' map coordinate relative to the observer robot [x,y,z]
        :return: occupancy map
        """

        scale = min(self.max_x, self.max_y)
        robot_range = max(1, int(math.floor(self.map_size * self.robot_size / scale / 2)))

        occupancy_map = (
            np.ones((self.map_size + 2 * robot_range, self.map_size + 2 * robot_range)) * 255
        )
        try:
            for world_points in position_list_local:
                if is_valid_point(world_points,sensor_range=self.max_x,sensor_view_angle=self.sensor_view_angle)==False:
                    continue
                map_points = self.world_to_map(world_points, self.map_size, self.max_x, self.max_y)
                if map_points == None:
                    continue
                x = map_points[0]
                y = map_points[1]
                for m in range(-robot_range, robot_range, 1):
                    for n in range(-robot_range, robot_range, 1):
                        occupancy_map[x + m][y + n] = 0
        except:
            pass
        occupancy_map = occupancy_map[
            robot_range:-robot_range, robot_range:-robot_range
        ]
        if self.position_encoding:
            occupancy_map=occupancy_map*self.position_encoding_matrix
        # occupancy_map = preprocess(occupancy_map)
        return occupancy_map
    def generate_map_partial(
        self,
        position_list_local,
    ):

        """
        Generate occupancy map with partially observation
        :param position_list_local: All robots' map coordinate relative to the observer robot [x,y,z]
        :return: occupancy map
        """

        scale = min(self.max_x, self.max_y)/2
        robot_range = max(1, int(math.floor(self.map_size * self.robot_size / scale)))
        occupancy_map = (
            np.ones((self.map_size + 2 * robot_range, self.map_size + 2 * robot_range)) * 255
        )
        try:
            for world_points in position_list_local:
                if is_valid_point(world_points,sensor_range=self.max_x,sensor_view_angle=self.sensor_view_angle)==False:
                    continue
                transformed_x = world_points[0] * math.sqrt(2) - world_points[1] * math.sqrt(2) - self.max_x
                transformed_y = world_points[0] * math.sqrt(2) + world_points[1] * math.sqrt(2) - self.max_y
                transformed_world_points = [transformed_x, transformed_y, 0]
                map_points = self.world_to_map( transformed_world_points, self.map_size, self.max_x, self.max_y)
                if map_points == None:
                    continue
                x = map_points[0]+robot_range
                y = map_points[1]+robot_range

                for m in range(-robot_range, robot_range, 1):
                    for n in range(-robot_range, robot_range, 1):
                        occupancy_map[x + m][y + n] = 0

        except:
            pass

        occupancy_map = occupancy_map[
            robot_range:-robot_range, robot_range:-robot_range
        ]
        if self.position_encoding:
            occupancy_map=occupancy_map*self.position_encoding_matrix
        # occupancy_map = preprocess(occupancy_map)
        return occupancy_map
    def generate_map_one(self,position_lists_local):
        """
                Generate one occupancy map
        """
        if self.partial:
            return self.generate_map_partial(position_lists_local)
        else:
            return self.generate_map_all(position_lists_local)

    def generate_maps(
        self,
        position_lists_local,
    ):

        """
        Generate occupancy map
        :param position_lists_local: All robots' map coordinate
        :return: A list of occupancy maps
        """
        maps = []
        for robot_index in range(len(position_lists_local)):
            occupancy_map = self.generate_map_one(
                position_lists_local[robot_index])
            maps.append(occupancy_map)
        return np.array(maps)



if __name__ == "__main__":
    map_simulator=MapSimulator(sensor_view_angle= 2*math.pi, local=True,partial=False)

    data = "C:\\Users\\xinchi\\multi_robot_formation\\scripts\\plots\\ViT_4\\3\\trace.npy"
    pose_array=np.load(data)
    print(pose_array.shape)
    pose_array=np.transpose(pose_array, (1, 0, 2))
    robot_num=pose_array.shape[0]

    time=1500

    pose_list=pose_array[:,time,:]

    position_lists_local = global_to_local(pose_list)
    for index in range(0, robot_num):
        occupancy_map = map_simulator.generate_map_one(position_lists_local[index])
        occupancy_map=occupancy_map[20:80,20:80]
        # for i in range(occupancy_map.shape[0]):
        #     for j in range(occupancy_map.shape[1]):
        #         if occupancy_map[i][j]==255:
        #             occupancy_map[i][j]=0
        #         else:
        #             occupancy_map[i][j] =255
        cv2.imshow("robot view " + str(index), np.array(occupancy_map))
        cv2.waitKey(0)
        cv2.imwrite(f"robot view {time} {index} .png".format(time,index) , np.array(occupancy_map))
    # position_list_local = [[-0.35, 0.3, 0.],
    #                        [0.3, 0.3, 0.],
    #                        [0., 0., 0.],
    #                        [-0.3, -0.3, 0.],
    #                        [0.3, -0.3, 0.], ]
    #
    #
    # print(position_list_local)
    # occupancy_map = map_simulator.generate_map_one(position_list_local)
    # cv2.imshow("robot view " + str(1), np.array(occupancy_map))
    # cv2.waitKey(0)

# print(math.sin(arctan(-1.732,-1)))
