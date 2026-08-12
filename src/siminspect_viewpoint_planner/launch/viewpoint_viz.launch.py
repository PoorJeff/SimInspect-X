from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    gen = Node(package="siminspect_viewpoint_planner", executable="candidate_generator.py", name="candidate_generator")
    viz = Node(package="siminspect_viewpoint_planner", executable="viewpoint_markers.py", name="viewpoint_markers")
    rv  = Node(package="rviz2", executable="rviz2", name="rviz2",
        arguments=["-d", ""], output="screen")
    return LaunchDescription([gen, viz, rv])
