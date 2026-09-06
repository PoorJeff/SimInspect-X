cmake_minimum_required(VERSION 3.8)
project(siminspect_bringup)

find_package(ament_cmake REQUIRED)
find_package(ament_cmake_python REQUIRED)

ament_python_install_package(${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_demo_config test/test_demo_config.py)
  ament_add_pytest_test(test_component_graph test/test_component_graph.py)
  ament_add_pytest_test(test_run_artifacts test/test_run_artifacts.py)
  ament_add_pytest_test(test_acceptance test/test_acceptance.py)
  ament_add_pytest_test(test_readiness test/test_readiness.py)
  ament_add_pytest_test(test_process_supervisor test/test_process_supervisor.py)
endif()

ament_package()
