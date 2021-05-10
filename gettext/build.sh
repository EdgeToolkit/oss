./configure HELP2MAN=/bin/true \
          EMACS=no \
          --disable-nls \
          --disable-dependency-tracking \
          --enable-relocatable \
          --disable-c++ \
          --disable-java \
          --disable-csharp \
          --disable-libasprintf \
          --disable-curses \
          --with-libiconv-prefix="/t/.epm/data/libiconv/1.16/_/_/package/127af201a4cdf8111e2e08540525c245c9b3b99e" \
          --disable-static \
          --disable-shared \
          --target=pe-x86-64 \
          --host=x86_64-w64-mingw32 \
          --prefix="/t/.epm/data/gettext/0.20.1/_/_/build/e87d840e83948069b18edafc38807b9408e81abe" \
          CC="/t/.epm/data/automake/1.16.2/_/_/package/3e48e69237f7f2196164383ef9dedf0f93cbf249/bin/share/automake-1.16/compile cl -nologo" \
          LD=link \
          NM="dumpbin -symbols" \
          STRIP=: \
          AR="/t/.epm/data/automake/1.16.2/_/_/package/3e48e69237f7f2196164383ef9dedf0f93cbf249/bin/share/automake-1.16/ar-lib lib" \
          RANLIB=: \
          RC="windres --target=pe-x86-64" \
          WINDRES="windres --target=pe-x86-64"
          
