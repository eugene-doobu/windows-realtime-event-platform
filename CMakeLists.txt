cmake_minimum_required(VERSION 3.23)

project(simlab_engine LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Python COMPONENTS Interpreter Development.Module REQUIRED)
find_package(pybind11 CONFIG REQUIRED)

pybind11_add_module(simlab_cpp
  bindings/python_module.cpp
  cpp/src/graph.cpp
  cpp/src/kernel.cpp
  cpp/src/metrics.cpp
  cpp/src/population.cpp
)

target_include_directories(simlab_cpp PRIVATE cpp/include)

install(TARGETS simlab_cpp DESTINATION simlab)

