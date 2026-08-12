cmake_minimum_required(VERSION 3.8)
project(siminspect_viewpoint_planner)
find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)
ament_python_install_package(${PROJECT_NAME})
install(DIRECTORY launch DESTINATION share/${PROJECT_NAME})
install(PROGRAMS
  ${PROJECT_NAME}/candidate_generator.py
  ${PROJECT_NAME}/viewpoint_markers.py
  DESTINATION lib/${PROJECT_NAME}
)
if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_dummy test/test_dummy.py)
endif()
ament_package()
