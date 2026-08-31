cmake_minimum_required(VERSION 3.8)
project(siminspect_sim)

find_package(ament_cmake REQUIRED)

install(DIRECTORY worlds models DESTINATION share/${PROJECT_NAME})

ament_environment_hooks(
  "${CMAKE_CURRENT_SOURCE_DIR}/env-hooks/siminspect_sim.dsv.in"
)

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_world_assets test/test_world_assets.py)
endif()

ament_package()
