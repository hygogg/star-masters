# 第三者ソフトウェアの表記

**ドット絵・BGM・SE・ゲームコードはこのリポジトリで新規に作ったもの。**
例外は、DS版の文字表示に使う 5x7 フォントのデータ(下記、Pimoroni Ltd. / MIT)。

ドット絵は `generate_images.py` 内のASCIIグリッド、BGMは `generate_audio.py` 内の
音符データとしてソースに直接書かれており、スクリプトを再実行すれば
同じファイルがバイト単位で再現される。生成スクリプトはPython標準ライブラリのみを使い、
ネットワークアクセスも外部ファイルの読み込みも行わない。

---

## このリポジトリに含まれる第三者のもの

### enchant.js v0.8.3 — MIT License

`shooter/lib/enchant.js`

ブラウザ版が使っているゲームライブラリ。
[公式リポジトリ](https://github.com/wise9/enchant.js) のタグ `v0.8.3` の
`dev/src/*.js` を、公式のビルド順(`Gruntfile.coffee` の `concat` 定義)で連結したもの。

```
enchant.js v0.8.3
http://enchantjs.com

Copyright Ubiquitous Entertainment Inc.
Released under the MIT license.
```

MITは「複製物に著作権表示と許諾表示を含めること」を条件とする。
表記はファイル冒頭に保持している。DS版では使っていない。

### 5x7 フォントのグリフデータ — MIT License

`shooter/tools/generate_nds_gfx.py` の `FONT57`(ASCII 32〜95 の64文字)と、
そこから生成される `shooter-nds/source/gfx_data.c` の `font_tiles`。
DS版のゲーム内の文字はすべてこのフォントで描かれる。

出典: [pimoroni/microdot-phat `library/microdotphat/font.py`](https://github.com/pimoroni/microdot-phat/blob/47f9cc35e6ed3523d02b9d5c6453cd7ad3eb73fc/library/microdotphat/font.py)
(コミット `47f9cc3`)の `font` 辞書の 32〜95 を、値を変えずに使っている。
定義箇所と生成ファイルの両方に出典と著作権表示を書いてある。

```
MIT License

Copyright (c) 2017 Pimoroni Ltd.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

> 以前の `FONT57` は出典の記録がなかった。Pimoroni版と照合すると64文字中58文字が一致し、
> 異なっていたのは `*` `M` `W` `Y` `[` `]` の6文字だけだった。
> 出典を明確にするため、64文字すべてをPimoroni版の公開データから取り直している。
> ブラウザ版の文字はブラウザの "Courier New" / monospace で描画しており、フォントは同梱していない。

---

## DS版のROMに組み込まれるもの(このリポジトリには含まれない)

DS版をビルドすると、devkitPro が配布する以下が `.nds` に組み込まれる。
**ビルド済みの `.nds` はこのリポジトリに含めていない**ため、
リポジトリの配布についてはこれらの表記義務は発生しない。

版は、下記「確認したビルド環境」のコンテナで実際にビルドし、リンクマップ
(`build/star-masters.map`)と `dkp-pacman -Q` で確かめたもの。

| | 版 | どこに入るか | ライセンス | ROMを配る時の表記 |
|---|---|---|---|---|
| calico | 1.2.0 | ARM9 (`libcalico_ds9.a`) と ARM7 | ZPL 2.1 | **必要**(著作権表示・条件・免責文を添付) |
| default-arm7 | 0.8.4 | ARM7 バイナリ `ds7_maine.elf` | ZPL 2.1 | **必要** |
| libnds | 2.0.2 | ARM9 (`libnds9.a`) | zlib | 不要(「appreciated but is not required」)。同梱はしている |
| maxmod | 2.1.0 | ARM9 (`libmm9.a`) と ARM7 | ISC | **必要**("appear in all copies") |
| newlib (devkitPro版) | 4.6.0.20260123 | ARM9 (`libg.a`, `libsysbase.a`) | BSD系の集合 | **必要**(多くの項目が binary form での表記を要求) |
| libgcc / crt*.o | GCC 16.1.0 | ARM9 | GPLv3 + GCC Runtime Library Exception 3.1 | 不要(例外によりプログラム側に義務は生じない)。参考として同梱 |
| フォントデータ | — | ARM9 (`font_tiles`) | MIT | **必要** |

- calico の著作権表示はソース各ファイルの SPDX ヘッダ(`Copyright fincs, devkitPro`)による。
  default-arm7 も同じ。
- dswifi は組み込まれない。ARM9 側の `libdswifi9` はリンクしておらず、
  `ds7_maine.elf` 内の Wi-Fi ドライバは calico の一部(`wifi.ntr.c` 等)。
- devkitarm-crtls はリンカスクリプトと specs のみで、コードはROMに入らない
  (crt0 は calico の `ds9.specs` 経由)。

### ROMを配布・販売する場合

[`shooter-nds/licenses/`](shooter-nds/licenses/) に、上表のすべてについて
著作権表示とライセンス全文を収めてある。**ROMと一緒にこのフォルダを配る。**

```sh
cd shooter-nds
./make-dist.sh v1.0.0
# → dist/star-masters-v1.0.0.zip
#    star-masters.nds / licenses/ / BUILD-INFO.txt
```

`make-dist.sh` は下記のイメージをダイジェストで固定して通常ビルドし、
ROMのSHA-256・gitコミット・パッケージの版を `BUILD-INFO.txt` に記録して ZIP にまとめる。
`latest` タグは中身が更新されるため、別のイメージでビルドした場合は
`BUILD-INFO.txt` の版と `licenses/` の版を突き合わせ、変わっていればライセンス文を取り直すこと。

### 確認したビルド環境(2026-11-07)

```
image   devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5
        (created 2026-06-10)

calico            1.2.0-1
default-arm7      0.8.4-4
libnds            2.0.2-1
maxmod-nds        2.1.0-2
devkitarm-newlib  4.6.0.20260123-5
devkitarm-gcc     16.1.0-1
devkitARM         r68-1
ndstool           2.3.1-1
```

ライセンス文の取得元:

| ファイル | 取得元 |
|---|---|
| `libnds-zlib.txt` | 上記コンテナの `$DEVKITPRO/libnds/libnds_license.txt` |
| `maxmod-ISC.txt` | 上記コンテナの `$DEVKITPRO/libnds/maxmod_license.txt` |
| `calico-ZPL-2.1.txt` | [devkitPro/calico](https://github.com/devkitPro/calico/blob/v1.2.0/COPYING) タグ `v1.2.0` の `COPYING` |
| `default-arm7-ZPL-2.1.txt` | [devkitPro/default-arm7](https://github.com/devkitPro/default-arm7/blob/v0.8.4/COPYING) タグ `v0.8.4` の `COPYING` |
| `newlib-COPYING.NEWLIB.txt` | [devkitPro/newlib](https://github.com/devkitPro/newlib/blob/devkitPro/COPYING.NEWLIB) ブランチ `devkitPro`(コミット `57bd8e1`、パッケージのビルド日と同日) |
| `gcc-runtime-library-exception-3.1.txt` | [gcc-mirror/gcc](https://github.com/gcc-mirror/gcc/blob/releases/gcc-16.1.0/COPYING.RUNTIME) `releases/gcc-16.1.0` の `COPYING.RUNTIME` |
| `font-pimoroni-MIT.txt` | [pimoroni/microdot-phat](https://github.com/pimoroni/microdot-phat/blob/47f9cc35e6ed3523d02b9d5c6453cd7ad3eb73fc/LICENSE) の `LICENSE` |

コンテナには calico・newlib・GCC のライセンス文が入っていないため、
この3つはパッケージの版に対応する上流のタグ/ブランチから取っている。

---

## 土台にした定型コード

### shooter-nds/Makefile

devkitPro が配布する NDS サンプル
(`$DEVKITPRO/examples/nds/audio/maxmod/basic_sound/Makefile`)を土台に、
ターゲット名・ROMヘッダ・音源ディレクトリ・`CFLAGS_EXTRA` を追加したもの。
devkitPro のサンプル Makefile は、この種のプロジェクトの定型ひな形として
配布・利用されている。

### shooter/serve.mjs

同じ作業ディレクトリにあった `ruin-runner/serve.mjs`(このリポジトリの作者自身のコード)を
土台に、`.wav` の MIME タイプとポート番号を変えたもの。第三者コードではない。

---

## 参考にした技術資料(コードの取り込みはしていない)

- [GBATEK](https://problemkaputt.de/gbatek.htm) — DSのハードウェア仕様(スプライト数128個/画面、最大64x64 など)
- ProTracker MOD フォーマットの仕様 — `generate_nds_audio.py` の MOD 書き出しに使用
- PNG 仕様(RFC 2083) — `generate_images.py` の PNG 書き出しに使用
