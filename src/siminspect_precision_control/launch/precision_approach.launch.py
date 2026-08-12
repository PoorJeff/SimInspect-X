import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    desired_distance = LaunchConfiguration("desired_distance_m", default="0.8")
    radius_mult = LaunchConfiguration("approach_radius_multiplier", default="2.0")
    timeout = LaunchConfiguration("timeout_s", default="30.0")

    handoff_node = Node(
        package="siminspect_precision_control",
        executable="handoff_manager.py",
        name="handoff_manager",
        parameters=[{
            "desired_distance_m": desired_distance,
            "approach_radius_multiplier": radius_mult,
            "timeout_s": timeout,
        }],
        output="screen",
    )

    controller_node = Node(
        package="siminspect_precision_control",
        executable="controller_interface.py",
        name="controller_interface",
        output="screen",
    )

    return LaunchDescription([
        DeclareLaunchArgument("desired_distance_m", default_value="0.8"),
        DeclareLaunchArgument("approach_radius_multiplier", default_value="2.0"),
        DeclareLaunchArgument("timeout_s", default_value="30.0"),
        handoff_node,
        controller_node,
    ])