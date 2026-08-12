import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
def generate_launch_description():
    pkg = get_package_share_directory('siminspect_localization')
    slam_cfg = os.path.join(pkg, 'config', 'slam.yaml')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    # EKF
    ekf = IncludeLaunchDescription(PythonLaunchDescriptionSource([pkg, '/launch/ekf.launch.py']))
    # SLAM Toolbox
    slam = Node(package='slam_toolbox', executable='async_slam_toolbox_node', name='slam_toolbox',
        parameters=[slam_cfg, {'use_sim_time': use_sim_time}])
    return LaunchDescription([DeclareLaunchArgument('use_sim_time', default_value='true'), ekf, slam])
