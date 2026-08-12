import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
def generate_launch_description():
    pkg = get_package_share_directory('siminspect_localization')
    loc_cfg = os.path.join(pkg, 'config', 'localization.yaml')
    map_file = LaunchConfiguration('map_file', default=os.path.join(pkg, 'config', 'map', 'siminspect_plant'))
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    # EKF
    ekf = IncludeLaunchDescription(PythonLaunchDescriptionSource([pkg, '/launch/ekf.launch.py']))
    # SLAM Toolbox in localization mode
    loc = Node(package='slam_toolbox', executable='localization_slam_toolbox_node', name='slam_toolbox',
        parameters=[loc_cfg, {'map_file_name': map_file, 'use_sim_time': use_sim_time}],
        remappings=[('map', '/map')])
    return LaunchDescription([DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('map_file', default_value=os.path.join(pkg, 'config', 'map', 'siminspect_plant')),
        ekf, loc])
