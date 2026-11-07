STAR MASTERS (Nintendo DS) - Third-party notices
================================================

star-masters.nds contains the following third-party software and data.
Each file in this folder holds the copyright notice and the full license
text for one component.

  Component                  Version              License        File
  -------------------------  -------------------  -------------  ------------------------------------
  calico (ARM9 + ARM7)       1.2.0                ZPL 2.1        calico-ZPL-2.1.txt
  default-arm7 (ARM7 binary  0.8.4                ZPL 2.1        default-arm7-ZPL-2.1.txt
    ds7_maine.elf)
  libnds                     2.0.2                zlib           libnds-zlib.txt
  maxmod (ARM9 + ARM7)       2.1.0                ISC            maxmod-ISC.txt
  newlib (devkitPro fork)    4.6.0.20260123       BSD-style      newlib-COPYING.NEWLIB.txt
    incl. libsysbase                              collection
  libgcc / crt*.o            GCC 16.1.0           GPLv3 + GCC    gcc-runtime-library-exception-3.1.txt
                                                  Runtime Lib.
                                                  Exception 3.1
  5x7 font glyph data        commit 47f9cc3       MIT            font-pimoroni-MIT.txt
    (Pimoroni microdot-phat)

The exact build environment (container image digest and package versions)
is recorded in BUILD-INFO.txt next to the ROM.

Not included: dswifi (the ARM9 Wi-Fi library is not linked; the ARM7 Wi-Fi
driver inside ds7_maine.elf is part of calico).

The graphics, music, sound effects and game code of STAR MASTERS itself
were created for this project. This software is unofficial homebrew and is
not affiliated with, endorsed or licensed by Nintendo.


STAR MASTERS（ニンテンドーDS版）第三者ソフトウェアの表記
------------------------------------------------------

star-masters.nds には上表の第三者ソフトウェアとデータが含まれています。
このフォルダの各ファイルに、それぞれの著作権表示とライセンス全文を収めています。

ビルド環境（コンテナイメージのダイジェストとパッケージの版）は、
ROMと同じ場所の BUILD-INFO.txt に記録しています。

ゲーム本体のドット絵・BGM・効果音・プログラムは本プロジェクトで制作したものです。
文字表示に使うフォントデータのみ、Pimoroni Ltd. が MIT ライセンスで公開している
データを使用しています。

本ソフトウェアは任天堂とは関係のない非公式の自作ソフト（homebrew）です。
