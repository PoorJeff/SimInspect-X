import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    pkg = "siminspect_description"
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")
    world = LaunchConfiguration("world", default="empty.sdf")

    robot_desc = Command([
        FindExecutable(name="xacro"), " ",
        PathJoinSubstitution([FindPackageShare(pkg), "urdf", "siminspect.urdf.xacro"]),
    ])

    rsp = Node(package="robot_state_publisher", executable="robot_state_publisher",
        parameters=[{"robot_description": robot_desc, "use_sim_time": use_sim_time}])

    gz_spawn = Node(package="ros_gz_sim", executable="create",
        arguments=["-name", "siminspect_amr", "-topic", "robot_description", "-x", "0.0", "-y", "0.0", "-z", "0.12", "-Y", "0.0"])

    gz_server = ExecuteProcess(cmd=["gz", "sim", "-s", "-r", world], output="screen")

    gz_gui = ExecuteProcess(cmd=["gz", "sim", "-g"], output="screen",
        condition=IfCondition(LaunchConfiguration("gui", default="false")))

    bridges = [
        "/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan",
        "/imu/data@sensor_msgs/msg/Imu@gz.msgs.IMU",
        "/camera/image_raw@sensor_msgs/msg/Image@gz.msgs.Image",
        "/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo",
        "/wheel/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry",
    ]

    gz_bridge = Node(package="ros_gz_bridge", executable="parameter_bridge",
        arguments=bridges,
        parameters=[{"use_sim_time": use_sim_time}],
        remappings=[("/camera/image_raw", "/camera/image_raw"),
                    ("/camera/camera_info", "/camera/camera_info")])

    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        DeclareLaunchArgument("gui", default_value="false"),
        DeclareLaunchArgument("world", default_value="empty.sdf"),
        gz_server, gz_gui, rsp, gz_bridge, gz_spawn,
    ])
