cmake_minimum_required(VERSION 3.14)
project(HuaweiCModel VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find or fetch yaml-cpp
find_package(yaml-cpp QUIET)
if(NOT yaml-cpp_FOUND)
    include(FetchContent)
    FetchContent_Declare(
        yaml-cpp
        GIT_REPOSITORY https://github.com/jbeder/yaml-cpp.git
        GIT_TAG 0.8.0
    )
    FetchContent_MakeAvailable(yaml-cpp)
endif()

# Core library
add_library(nocsim_core
    src/config.cpp
    src/stats.cpp
    src/trace.cpp
    src/simulator.cpp
    src/ring.cpp
    src/cross_station.cpp
    src/rbrg_l1.cpp
    src/rbrg_l2.cpp
)
target_include_directories(nocsim_core PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include)
target_link_libraries(nocsim_core PUBLIC yaml-cpp)

# Main executable
add_executable(nocsim
    src/main.cpp
)
target_link_libraries(nocsim PRIVATE nocsim_core)

# Tests (GoogleTest)
enable_testing()
include(FetchContent)
FetchContent_Declare(
  googletest
  URL https://github.com/google/googletest/archive/03597a01ee50ed33e9dfd640b249b4be3799d395.zip
)
# For Windows: Prevent overriding the parent project's compiler/linker settings
set(gtest_force_shared_crt ON CACHE BOOL "" FORCE)
FetchContent_MakeAvailable(googletest)

add_executable(run_tests
    tests/test_config.cpp
    tests/test_simulator.cpp
    tests/test_single_ring.cpp
    tests/test_full_ring.cpp
    tests/test_i_tag.cpp
    tests/test_e_tag.cpp
    tests/test_rbrg_l1.cpp
    tests/test_rbrg_l1_backpressure.cpp
    tests/test_rbrg_l2.cpp
    tests/test_rbrg_l2_credit.cpp
)
target_link_libraries(run_tests PRIVATE nocsim_core GTest::gtest_main)

include(GoogleTest)
gtest_discover_tests(run_tests)
