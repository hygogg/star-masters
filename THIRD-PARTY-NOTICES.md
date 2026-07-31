# 第三者ソフトウェアの表記

このリポジトリに含まれる、他者が権利を持つソフトウェアの一覧。
**ドット絵・BGM・SE・ゲームコードはすべてこのリポジトリで新規に作ったもので、
外部から取り込んだ素材は含まれていない**(`shooter/tools/` の生成スクリプトが
ドット絵のグリッドと音符データから作り出している)。

---

## 1. enchant.js v0.8.3 — MIT License

`shooter/lib/enchant.js`

ブラウザ版が使っているゲームライブラリ。
[公式リポジトリ](https://github.com/wise9/enchant.js) の タグ `v0.8.3` の
`dev/src/*.js` を公式のビルド順(`Gruntfile.coffee` の `concat` 定義)で連結したもの。
ライセンス表記はファイル冒頭に保持している。

```
Copyright Ubiquitous Entertainment Inc.
Released under the MIT license.
```

---

## 2. libnds — zlib風ライセンス

DS版のROM `shooter-nds/star-masters.nds` に静的リンクされている
(ソースはこのリポジトリには含まれない。devkitPro が配布)。

```
Copyright (C) 2005
    Michael Noland (joat)
    Jason Rogers (dovoto)
    Dave Murphy (WinterMute)

This software is provided 'as-is', without any express or implied
warranty.  In no event will the authors be held liable for any
damages arising from the use of this software.

Permission is granted to anyone to use this software for any
purpose, including commercial applications, and to alter it and
redistribute it freely, subject to the following restrictions:

1. The origin of this software must not be misrepresented; you
   must not claim that you wrote the original software. If you use
   this software in a product, an acknowledgment in the product
   documentation would be appreciated but is not required.

2. Altered source versions must be plainly marked as such, and
   must not be misrepresented as being the original software.

3. This notice may not be removed or altered from any source
   distribution.
```

---

## 3. maxmod — ISC License

DS版のサウンドドライバ。ROM `shooter-nds/star-masters.nds` に静的リンクされている。

```
Nintendo DS & Gameboy Advance Sound System

Copyright (c) 2008, Mukunda Johnson (mukunda@maxmod.org)

Permission to use, copy, modify, and/or distribute this software for any
purpose with or without fee is hereby granted, provided that the above
copyright notice and this permission notice appear in all copies.

THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.
```

`audio/*.mod` と `audio/*.wav` を `soundbank.bin` にまとめる `mmutil` も
maxmod プロジェクトのツール(ビルド時のみ使用、リポジトリには含まれない)。

---

## 4. shooter-nds/Makefile

devkitPro が配布する NDS サンプル
(`$DEVKITPRO/examples/nds/audio/maxmod/basic_sound/Makefile`)を土台にして、
ターゲット名・ROMヘッダ・音源ディレクトリ・`CFLAGS_EXTRA` を追加したもの。
devkitPro のサンプル Makefile は、この種のプロジェクトの定型ひな形として
配布・利用されている。

---

## 5. shooter/serve.mjs

同じ作業ディレクトリにあった `ruin-runner/serve.mjs`(このリポジトリの作者自身のコード)を
土台に、`.wav` の MIME タイプとポート番号を変えたもの。第三者コードではない。

---

## 参考にした技術資料(コードの取り込みはしていない)

- [GBATEK](https://problemkaputt.de/gbatek.htm) — DSのハードウェア仕様(スプライト数・サイズ制限など)
- ProTracker MOD フォーマットの仕様 — `generate_nds_audio.py` の MOD 書き出しに使用
- PNG 仕様(RFC 2083) — `generate_images.py` の PNG 書き出しに使用
