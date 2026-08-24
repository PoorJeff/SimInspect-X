from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

def generate_launch_description():
    controller_type = LaunchConfiguration("controller_type")

    controller_node = Node(
        package="siminspect_precision_control",
        executable="controller_interface.py",
        name="controller_interface",
        parameters=[{"controller_type": controller_type}],
        output="screen",
    )

    return LaunchDescription([
        DeclareLaunchArgument("controller_type", default_value="pid"),
        controller_node,
    ])
