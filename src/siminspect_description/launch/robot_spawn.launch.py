import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    pkg = "siminspect_description"
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")
    world = LaunchConfiguration("world", default="empty.sdf")
    publish_ground_truth = LaunchConfiguration("publish_ground_truth")

    robot_desc = Command([
        FindExecutable(name="xacro"), " ",
        PathJoinSubstitution([FindPackageShare(pkg), "urdf", "siminspect.urdf.xacro"]),
    ])

    rsp = Node(package="robot_state_publisher", executable="robot_state_publisher",
        parameters=[{"robot_description": ParameterValue(robot_desc, value_type=str),
                     "use_sim_time": use_sim_time}])

    gz_spawn = Node(package="ros_gz_sim", executable="create",
        arguments=["-name", "siminspect_amr", "-topic", "robot_description", "-x", "0.0", "-y", "0.0", "-z", "0.12", "-Y", "0.0"])

    # Keep the server headless while enabling OGRE rendering for GPU lidar and
    # camera sensors.  ``-s`` alone creates the sensor topics but does not
    # produce rendering-backed samples, which prevents SLAM and camera
    # acceptance checks from receiving data in CPU/headless runs.
    gz_server = ExecuteProcess(cmd=["gz", "sim", "-s", "--headless-rendering", "-r", world], output="screen")

    gz_gui = ExecuteProcess(cmd=["gz", "sim", "-g"], output="screen",
        condition=IfCondition(LaunchConfiguration("gui", default="false")))

    bridges = [
        "/scan@sensor_msgs/msg/LaserScan@gz.msgs.LaserScan",
        "/camera/image_raw@sensor_msgs/msg/Image@gz.msgs.Image",
        "/camera/camera_info@sensor_msgs/msg/CameraInfo@gz.msgs.CameraInfo",
        "/wheel/odometry@nav_msgs/msg/Odometry@gz.msgs.Odometry",
        "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
        "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
        "/pose/info@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
    ]

    gz_bridge = Node(package="ros_gz_bridge", executable="parameter_bridge",
        arguments=bridges,
        parameters=[{"use_sim_time": use_sim_time}],
        remappings=[("/scan", "/scan_raw"),
                    ("/camera/image_raw", "/camera/image_raw"),
                    ("/camera/camera_info", "/camera/camera_info")])

    imu_bridge = Node(
        package="ros_gz_bridge", executable="parameter_bridge", name="imu_bridge",
        arguments=["/imu/data@sensor_msgs/msg/Imu[gz.msgs.IMU"],
        parameters=[{"use_sim_time": use_sim_time, "override_frame_id": "imu_link"}],
    )

    scan_frame_relay = Node(
        package="siminspect_localization",
        executable="laser_scan_frame_relay.py",
        name="laser_scan_frame_relay",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    gt_pub = Node(
        package="siminspect_benchmark",
        executable="ground_truth_publisher.py",
        name="ground_truth_publisher",
        parameters=[{"use_sim_time": use_sim_time}],
        condition=IfCondition(publish_ground_truth),
    )
    return LaunchDescription([
        DeclareLaunchArgument("use_sim_time", default_value="true"),
        DeclareLaunchArgument("gui", default_value="false"),
        DeclareLaunchArgument("world", default_value="empty.sdf"),
        DeclareLaunchArgument("publish_ground_truth", default_value="false"),
        gz_server, gz_gui, rsp, gz_bridge, imu_bridge, scan_frame_relay, gz_spawn, gt_pub,
    ])
