CXX = g++
CXXFLAGS = -Wall -std=c++14

TARGET = noc_sim
SRCS = main.cpp Router.cpp Topology.cpp Routing.cpp
OBJS = $(SRCS:.cpp=.o)

TEST_TARGET = run_tests
TEST_SRCS = tests/test_topology.cpp tests/test_routing.cpp tests/test_router.cpp Router.cpp Topology.cpp Routing.cpp
TEST_OBJS = $(TEST_SRCS:.cpp=.o)
GTEST_LIBS = -lgtest -lgtest_main -pthread

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(OBJS) -lyaml-cpp

$(TEST_TARGET): $(TEST_OBJS)
	$(CXX) $(CXXFLAGS) -o $(TEST_TARGET) $(TEST_OBJS) $(GTEST_LIBS)

test: $(TEST_TARGET) all
	./$(TEST_TARGET)
	python3 tests/run_golden_tests.py

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET) $(TEST_OBJS) $(TEST_TARGET)
