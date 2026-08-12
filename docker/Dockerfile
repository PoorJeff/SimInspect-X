# SimInspect-X Dockerfile
# Ubuntu 24.04 + ROS 2 Jazzy + Gazebo Harmonic
# See ADR-001 and docs/05_TECH_STACK.md

FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# Locale and timezone
RUN apt-get update && apt-get install -y --no-install-recommends \
    locales \
    tzdata \
    && locale-gen en_US.UTF-8 \
    && update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*

ENV LANG=en_US.UTF-8

# ROS 2 Jazzy
RUN apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    curl \
    gnupg \
    lsb-release \
    && add-apt-repository universe \
    && curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
       > /etc/apt/sources.list.d/ros2.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    ros-jazzy-desktop \
    ros-jazzy-ros-gz \
    ros-jazzy-gz-ros2-control \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup \
    ros-jazzy-slam-toolbox \
    ros-jazzy-robot-localization \
    ros-jazzy-rosbag2 \
    python3-rosdep \
    python3-colcon-common-extensions \
    python3-vcstool \
    python3-pip \
    python3-yaml \
    ros-jazzy-ament-index-python \
    && rm -rf /var/lib/apt/lists/*

# Python packages for vision, control, analysis
RUN pip3 install --break-system-packages \
    numpy \
    scipy \
    matplotlib \
    pandas \
    opencv-python \
    osqp \
    pytest

# Gazebo Harmonic (standalone, for headless simulation)
RUN curl -sSL https://packages.osrfoundation.org/gazebo.gpg -o /usr/share/keyrings/gazebo-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/gazebo-archive-keyring.gpg] http://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
       > /etc/apt/sources.list.d/gazebo-stable.list \
    && apt-get update && apt-get install -y --no-install-recommends \
    gz-harmonic \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash siminspect \
    && echo "siminspect ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

USER siminspect
WORKDIR /home/siminspect

RUN echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc

CMD ["/bin/bash"]