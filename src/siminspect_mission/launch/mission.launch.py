import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")

    mission = Node(
        package="siminspect_mission",
        executable="mission_executor.py",
        name="mission_executor",
        output="screen",
    )

    # Dependencies: Nav2 + EKF + localisation
    nav_pkg = get_package_share_directory("siminspect_navigation")
    loc_pkg = get_package_share_directory("siminspect_localization")

    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([nav_pkg, "/launch/navigation.launch.py"]),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )
    loc = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([loc_pkg, "/launch/localization.launch.py"]),
        launch_arguments={"use_sim_time": use_sim_time}.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        nav2,
        loc,
        mission,
    ])