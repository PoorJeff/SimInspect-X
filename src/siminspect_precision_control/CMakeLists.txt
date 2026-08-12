cmake_minimum_required(VERSION 3.8)
project(siminspect_precision_control)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

install(PROGRAMS
  ${PROJECT_NAME}/controller_interface.py
  ${PROJECT_NAME}/handoff_manager.py
  ${PROJECT_NAME}/pid_controller.py
  ${PROJECT_NAME}/mpc_controller.py
  DESTINATION lib/${PROJECT_NAME}
)
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_handoff test/test_handoff.py)
  ament_add_pytest_test(test_pid_controller test/test_pid_controller.py)
  ament_add_pytest_test(test_mpc_controller test/test_mpc_controller.py)
endif()

ament_package()