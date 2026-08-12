import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
def generate_launch_description():
    pkg = get_package_share_directory('siminspect_navigation')
    params = os.path.join(pkg, 'config', 'nav2_params.yaml')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    nav2_pkg = get_package_share_directory('nav2_bringup')
    nav2 = IncludeLaunchDescription(PythonLaunchDescriptionSource([nav2_pkg, '/launch/bringup_launch.py']),
        launch_arguments={'params_file': params, 'use_sim_time': use_sim_time}.items())
    return LaunchDescription([DeclareLaunchArgument('use_sim_time', default_value='true'), nav2])
