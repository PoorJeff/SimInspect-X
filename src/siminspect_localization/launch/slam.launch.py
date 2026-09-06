import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
def generate_launch_description():
    pkg = get_package_share_directory('siminspect_localization')
    slam_cfg = os.path.join(pkg, 'config', 'slam.yaml')
    slam_toolbox_pkg = get_package_share_directory('slam_toolbox')
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    include_ekf = LaunchConfiguration('include_ekf', default='false')
    # EKF
    ekf = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([pkg, '/launch/ekf.launch.py']),
        launch_arguments={'use_sim_time': use_sim_time}.items(),
        condition=IfCondition(include_ekf),
    )
    # Use the upstream lifecycle launch so mapping is configured and activated
    # before Nav2 waits for the map -> odom transform.
    slam = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(slam_toolbox_pkg, 'launch', 'online_async_launch.py')
        ),
        launch_arguments={
            'slam_params_file': slam_cfg,
            'use_sim_time': use_sim_time,
            'autostart': 'true',
            'use_lifecycle_manager': 'false',
        }.items(),
    )
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('include_ekf', default_value='false'),
        ekf,
        slam,
    ])
