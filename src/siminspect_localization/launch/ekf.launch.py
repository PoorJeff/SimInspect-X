import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
def generate_launch_description():
    cfg = os.path.join(get_package_share_directory('siminspect_localization'), 'config', 'ekf.yaml')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    ekf = Node(package='robot_localization', executable='ekf_node', name='ekf_filter_node',
        parameters=[cfg, {'use_sim_time': use_sim_time}],
        remappings=[('odometry/filtered', '/odometry/filtered')])
    return LaunchDescription([DeclareLaunchArgument('use_sim_time', default_value='true'), ekf])
