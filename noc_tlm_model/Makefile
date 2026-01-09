SYSTEMC_HOME ?= /usr/local/systemc-2.3.3
CXX = g++
CXXFLAGS = -Wall -std=c++11 -I$(SYSTEMC_HOME)/include
LDFLAGS = -L$(SYSTEMC_HOME)/lib-linux64 -lsystemc -Wl,-rpath=$(SYSTEMC_HOME)/lib-linux64

TARGET = noc_tlm_sim
SRCS = sc_main.cpp
OBJS = $(SRCS:.cpp=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CXX) $(CXXFLAGS) -o $(TARGET) $(OBJS) $(LDFLAGS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@

clean:
	rm -f $(OBJS) $(TARGET)
