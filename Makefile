MKDIR := mkdir -p
SRC_DIR := .
OBJ_DIR := ./obj
SRC_FILES := $(wildcard ./*.cpp)
OBJ_FILES := $(patsubst $(SRC_DIR)/%.cpp,$(OBJ_DIR)/%.o,$(SRC_FILES))
LDFLAGS := -llinuxcnc -lnml -lpthread
CXXFLAGS := -c -Wall -I. -I/usr/include -I/usr/include/linuxcnc

linuxcnc-gcode-server: $(OBJ_FILES)
	g++ -o $@ $^ $(LDFLAGS)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.cpp
	@ $(MKDIR) $(@D)
	g++ $(CXXFLAGS) -c -o $@ $<

clean:
	rm -rf $(OBJ_DIR)

stop:
	-pkill -9 -f linuxcnc || true
	-pkill -9 milltask || true
	-pkill -9 emcsvr || true
	-pkill -9 halcmd || true
	-pkill -9 linuxcnc-gcode-server || true


