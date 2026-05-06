cmake_minimum_required(VERSION 3.13)
project(hollowdetectorsim)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Geant4 REQUIRED COMPONENTS ui_all vis_all)
include(${Geant4_USE_FILE})

file(GLOB SOURCES ${PROJECT_SOURCE_DIR}/src/*.cc)
file(GLOB HEADERS ${PROJECT_SOURCE_DIR}/include/*.hh)

add_executable(hollowdetectorsim ${SOURCES} ${HEADERS})

target_include_directories(hollowdetectorsim PRIVATE
    ${PROJECT_SOURCE_DIR}/include
)

target_link_libraries(hollowdetectorsim PRIVATE ${Geant4_LIBRARIES})

if(TARGET Geant4::G4analysis)
    message(STATUS "Linking with Geant4::G4analysis")
    target_link_libraries(hollowdetectorsim PRIVATE Geant4::G4analysis)
else()
    message(WARNING "Geant4::G4analysis target not found. Build will proceed without the analysis library.")
endif()