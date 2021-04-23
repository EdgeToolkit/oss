# 
#
#
cmake_minimum_required(VERSION 3.10)

project(a52dec 
        VERSION 0.7.4
        LANGUAGES C)
        


if (MSVC)
  # Build with multiple processes
#  add_definitions(/MP)
  # MSVC warning suppressions
  add_definitions(
#    /wd4018 # 'expression' : signed/unsigned mismatch
#    /wd4065 # switch statement contains 'default' but no 'case' labels
#    /wd4146 # unary minus operator applied to unsigned type, result still unsigned
#    /wd4244 # 'conversion' conversion from 'type1' to 'type2', possible loss of data
#    /wd4251 # 'identifier' : class 'type' needs to have dll-interface to be used by clients of class 'type2'
#    /wd4267 # 'var' : conversion from 'size_t' to 'type', possible loss of data
#    /wd4305 # 'identifier' : truncation from 'type1' to 'type2'
#    /wd4307 # 'operator' : integral constant overflow
#    /wd4309 # 'conversion' : truncation of constant value
#    /wd4334 # 'operator' : result of 32-bit shift implicitly converted to 64 bits (was 64-bit shift intended?)
#    /wd4355 # 'this' : used in base member initializer list
#    /wd4506 # no definition for inline function 'function'
#    /wd4800 # 'type' : forcing value to bool 'true' or 'false' (performance warning)
#    /wd4996 # The compiler encountered a deprecated declaration.
  )

  # Suppress linker warnings about files with no symbols defined.
#  set(CMAKE_STATIC_LINKER_FLAGS /ignore:4221)

endif (MSVC)


include_directories(include )


##############################################################
#
# liba52dec
#
##############################################################
add_library(liba52 liba52/bit_allocate.c
                   liba52/bit_allocate.c
                   liba52/bitstream.c
                   liba52/downmix.c
                   liba52/imdct.c
                   liba52/parse.c)
target_include_directories (liba52 PRIVATE liba52 vc++)

##############################################################
#
# libao
#
##############################################################
add_library(libao libao/audio_out.c
                  libao/audio_out_aif.c
                  libao/audio_out_al.c
                  libao/audio_out_float.c
                  libao/audio_out_null.c
                  libao/audio_out_oss.c
                  libao/audio_out_peak.c
                  libao/audio_out_solaris.c
                  libao/audio_out_wav.c
                  libao/audio_out_win.c
                  libao/float2s16.c)
                  
target_include_directories(libao PRIVATE libao vc++)

##############################################################
#
# a52dec
#
##############################################################
add_executable(a52dec src/a52dec.c
                      src/getopt.c
                      src/gettimeofday.c)
target_include_directories(a52dec PRIVATE src vc++)
target_compile_definitions(a52dec PRIVATE HAVE_CONFIG_H)
target_link_libraries(a52dec liba52 libao winmm.lib)


##############################################################
#
# extract_a52
#
##############################################################
add_executable(extract_a52 src/extract_a52.c
                           src/getopt.c
                           src/gettimeofday.c)
target_include_directories(extract_a52 PRIVATE src vc++)
target_compile_definitions(extract_a52 PRIVATE HAVE_CONFIG_H)
target_link_libraries(extract_a52 liba52 libao winmm.lib)



file(GLOB HDRs include/*.h)
install(FILES ${HDRs} DESTINATION include/a52dec)

# Install configuration
install(TARGETS liba52 a52dec extract_a52 
        EXPORT  a52dec
        LIBRARY DESTINATION lib
        ARCHIVE DESTINATION lib
        RUNTIME DESTINATION bin
        PUBLIC_HEADER DESTINATION include)
