cmake_minimum_required(VERSION 3.10)

project(Q-T_lib)

# 设置输出目录
set(CMAKE_BINARY_DIR ${CMAKE_SOURCE_DIR}/build)
set(EXECUTABLE_OUTPUT_PATH ${CMAKE_BINARY_DIR}/bin)

# 查找已打包的 Q-T_lib.exe
find_file(QT_LIB_EXE Q-T_lib.exe PATHS ${CMAKE_SOURCE_DIR}/dist)

if(NOT QT_LIB_EXE)
    message(FATAL_ERROR "Q-T_lib.exe not found in dist directory. Please ensure it has been built with PyInstaller.")
endif()

# 安装 Q-T_lib.exe
install(FILES ${QT_LIB_EXE} DESTINATION .)

# 安装数据文件
install(FILES ${CMAKE_SOURCE_DIR}/etf_data.xlsx DESTINATION .)

# 提供构建和运行说明
message(STATUS "Q-T_lib project configured. Use 'cmake --build .' to build, and find the executable in build/bin.")
