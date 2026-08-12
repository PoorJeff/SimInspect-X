from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    eval_node = Node(package='siminspect_benchmark', executable='localisation_eval.py',
        name='localisation_eval', parameters=[{'use_sim_time': use_sim_time}], output='screen')
    return LaunchDescription([DeclareLaunchArgument('use_sim_time', default_value='true'), eval_node])
