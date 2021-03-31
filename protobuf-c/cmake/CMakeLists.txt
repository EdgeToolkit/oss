# Minimum CMake required
cmake_minimum_required(VERSION 3.10)

if(protobuf-c_VERBOSE)
  message(STATUS "protobuf-c Configuring...")
endif()

# CMake policies
cmake_policy(SET CMP0022 NEW)
# On MacOS use @rpath/ for target's install name prefix path
if (POLICY CMP0042)
  cmake_policy(SET CMP0042 NEW)
endif ()
# Clear VERSION variables when no VERSION is given to project()
if(POLICY CMP0048)
  cmake_policy(SET CMP0048 NEW)
endif()

# Project
project(protobuf-c)


# Options

option(protobuf-c_CXX11_ENABLE "enable C++ 11 compile feature." OFF)
option(protobuf-c_MSVC_STATIC_RUNTIME "MSVC Link static runtime libraries." OFF)
if(protobuf-c_CXX11_ENABLE)
    if (CYGWIN)
      set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=gnu++11")
    else()
      set(CMAKE_CXX_STANDARD 11)
      set(CMAKE_CXX_STANDARD_REQUIRED ON)
      set(CMAKE_CXX_EXTENSIONS OFF)
    endif()
endif(protobuf-c_CXX11_ENABLE)


if (MSVC)
  # Build with multiple processes
  add_definitions(/MP)
  # MSVC warning suppressions
  add_definitions(
    /wd4018 # 'expression' : signed/unsigned mismatch
    /wd4065 # switch statement contains 'default' but no 'case' labels
    /wd4146 # unary minus operator applied to unsigned type, result still unsigned
    /wd4244 # 'conversion' conversion from 'type1' to 'type2', possible loss of data
    /wd4251 # 'identifier' : class 'type' needs to have dll-interface to be used by clients of class 'type2'
    /wd4267 # 'var' : conversion from 'size_t' to 'type', possible loss of data
    /wd4305 # 'identifier' : truncation from 'type1' to 'type2'
    /wd4307 # 'operator' : integral constant overflow
    /wd4309 # 'conversion' : truncation of constant value
    /wd4334 # 'operator' : result of 32-bit shift implicitly converted to 64 bits (was 64-bit shift intended?)
    /wd4355 # 'this' : used in base member initializer list
    /wd4506 # no definition for inline function 'function'
    /wd4800 # 'type' : forcing value to bool 'true' or 'false' (performance warning)
    /wd4996 # The compiler encountered a deprecated declaration.
  )

# Suppress linker warnings about files with no symbols defined.
#  set(CMAKE_STATIC_LINKER_FLAGS /ignore:4221)
endif (MSVC)

# C/C++ file extension
set(C_SOURCE_FILE_EXTENSION *.c)
set(C_HEADER_FILE_EXTENSION *.c)
set(CXX_SOURCE_FILE_EXTENSION ${C_SOURCE_FILE_EXTENSION} *.cxx *cpp *.cc)
set(CXX_HEADER_FILE_EXTENSION ${C_HEADER_FILE_EXTENSION} *.hpp *.hxx)



if (BUILD_SHARED_LIBS)
  set(protobuf-c_BUILD_SHARED_LIBS_DEFAULT ON)
else (BUILD_SHARED_LIBS)
  set(protobuf-c_BUILD_SHARED_LIBS_DEFAULT OFF)
endif (BUILD_SHARED_LIBS)

option(protobuf-c_BUILD_SHARED_LIBS "Build Shared Libraries" ${protobuf-c_BUILD_SHARED_LIBS_DEFAULT})
  
set(protobuf-c_DEBUG_POSTFIX "d" CACHE STRING "Default debug postfix")
mark_as_advanced(protobuf-c_DEBUG_POSTFIX)

if (protobuf-c_BUILD_SHARED_LIBS)
  set(protobuf-c_SHARED_OR_STATIC "SHARED")
  add_definitions(-DPROTOBUF_C_USE_SHARED_LIB)
else (protobuf-c_BUILD_SHARED_LIBS)
  set(protobuf-c_SHARED_OR_STATIC "STATIC")
  # In case we are building static libraries, link also the runtime library statically
  # so that MSVCR*.DLL is not required at runtime.
  # https://msdn.microsoft.com/en-us/library/2kzt1wy3.aspx
  # This is achieved by replacing msvc option /MD with /MT and /MDd with /MTd
  # http://www.cmake.org/Wiki/CMake_FAQ#How_can_I_build_my_MSVC_application_with_a_static_runtime.3F
  if (MSVC AND protobuf-c_MSVC_STATIC_RUNTIME)
    foreach(flag_var
        CMAKE_CXX_FLAGS CMAKE_CXX_FLAGS_DEBUG CMAKE_CXX_FLAGS_RELEASE
        CMAKE_CXX_FLAGS_MINSIZEREL CMAKE_CXX_FLAGS_RELWITHDEBINFO)
      if(${flag_var} MATCHES "/MD")
        string(REGEX REPLACE "/MD" "/MT" ${flag_var} "${${flag_var}}")
      endif(${flag_var} MATCHES "/MD")
    endforeach(flag_var)
  endif (MSVC AND protobuf-c_MSVC_STATIC_RUNTIME)
endif (protobuf-c_BUILD_SHARED_LIBS)



get_filename_component(lib_source_dir ${protobuf-c_SOURCE_DIR}  PATH)
set(lib_source_dir ${lib_source_dir}/source_subfolder)
include_directories(${lib_source_dir} ${lib_source_dir}/protobuf-c)

if (MSVC)
  # Add the "lib" prefix for generated .lib outputs.
  set(LIB_PREFIX lib)
else (MSVC)
  # When building with "make", "lib" prefix will be added automatically by
  # the build tool.
  set(LIB_PREFIX)
endif (MSVC)

##############################################################
#
# protobuf-c library
#
##############################################################
set(_SRCs  ${lib_source_dir}/protobuf-c/protobuf-c.c)
set(_HDRs ${lib_source_dir}/protobuf-c/protobuf-c.h)

add_library(protobuf-c ${_SRCs} ${_HDRs})

if(BUILD_SHARED_LIBS)
  if(MSVC)
    target_compile_definitions(protobuf-c
        PUBLIC  PROTOBUF_C_EXPORT
        PRIVATE PROTOBUF_C_USE_DLLS)
  endif()

target_link_libraries(protobuf-c ${CONAN_LIBS})
endif()
source_group(TREE ${lib_source_dir} FILES  ${_SRCs} ${_HDRs})


# Install configuration
set(_cmakedir_desc "Directory relative to CMAKE_INSTALL to install the cmake configuration files")
if(NOT MSVC)
  set(CMAKE_INSTALL_CMAKEDIR "${CMAKE_INSTALL_LIBDIR}/cmake/protobuf-c" CACHE STRING "${_cmakedir_desc}")
else()
  set(CMAKE_INSTALL_CMAKEDIR "cmake" CACHE STRING "${_cmakedir_desc}")
endif()
mark_as_advanced(CMAKE_INSTALL_CMAKEDIR)

# Install configuration
set(_cmakedir_desc "Directory relative to CMAKE_INSTALL to install the cmake configuration files")
configure_file(protobuf-c-config.cmake.in
               ${CMAKE_INSTALL_CMAKEDIR}/protobuf-c-config.cmake @ONLY)


export(TARGETS protobuf-c
  NAMESPACE protobuf-c::
  FILE ${CMAKE_INSTALL_CMAKEDIR}/protobuf-c-targets.cmake )

install(EXPORT protobuf-c-targets
  DESTINATION "${CMAKE_INSTALL_CMAKEDIR}"
  NAMESPACE protobuf-c::
  COMPONENT protobuf-c-export)

install(DIRECTORY ${CMAKE_CURRENT_BINARY_DIR}/${CMAKE_INSTALL_CMAKEDIR}/
  DESTINATION "${CMAKE_INSTALL_CMAKEDIR}"
  COMPONENT protobuf-c-export
  PATTERN protobuf-c-targets.cmake EXCLUDE )

install(FILES ${lib_source_dir}/protobuf-c/protobuf-c.h DESTINATION  include/protobuf-c)
install(FILES ${lib_source_dir}/protobuf-c/protobuf-c.h DESTINATION  include/google/protobuf-c)
install(TARGETS protobuf-c EXPORT protobuf-c-targets
  RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR} COMPONENT protobuf-c
  LIBRARY DESTINATION ${CMAKE_INSTALL_LIBDIR} COMPONENT protobuf-c
  ARCHIVE DESTINATION ${CMAKE_INSTALL_LIBDIR} COMPONENT protobuf-c)


if(protobuf-c_VERBOSE)
    message(STATUS "protobuf-c Configuring done")
endif()