# 第三者ソフトウェアの表記

**ドット絵・BGM・SE・ゲームコードはすべてこのリポジトリで新規に作ったもので、
外部から取り込んだ素材は含まれていない。**
ドット絵は `generate_images.py` 内のASCIIグリッド、BGMは `generate_audio.py` 内の
音符データとしてソースに直接書かれており、スクリプトを再実行すれば
同じファイルがバイト単位で再現される。生成スクリプトはPython標準ライブラリのみを使い、
ネットワークアクセスも外部ファイルの読み込みも行わない。

---

## 同梱している第三者ソフトウェア

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
本リポジトリはこのファイル自体を同梱しているため表記が必要で、
表記はファイル冒頭に保持している。

これ以外に同梱している第三者のコード・素材はない。

---

## ビルド時にリンクされるもの(このリポジトリには含まれない)

DS版をビルドすると、devkitPro が配布する以下のライブラリが `.nds` に静的リンクされる。
**ビルド済みの `.nds` は意図的にこのリポジトリに含めていない**ため、
本リポジトリの配布に関してこれらの表記義務は発生しない。

| | ライセンス | 表記義務(バイナリ再配布時) |
|---|---|---|
| libnds | zlib風 | **不要**(条文に「appreciated but is not required」と明記) |
| maxmod | ISC | **必要**("appear in all copies") |
| newlib | BSD系の集合(57項目) | **必要**(34項目が binary form での表記を要求) |
| libgcc | GPLv3 + GCC Runtime Library Exception | 不要(例外条項によりバイナリ配布に義務は生じない) |

### ビルドした `.nds` を他人に配る場合

自分でビルドした `.nds` を配布・公開する場合は、上表のうち「必要」のものについて
配布物に著作権表示と許諾文を添える必要がある。具体的には:

- **maxmod** — `$DEVKITPRO/libnds/maxmod_license.txt`(ISC。Copyright (c) 2008, Mukunda Johnson)
- **newlib** — newlib の `COPYING.NEWLIB`
  ([sourceware.org](https://sourceware.org/git/?p=newlib-cygwin.git;a=blob_plain;f=COPYING.NEWLIB;hb=HEAD))

どちらも devkitPro のインストール先、または上記の配布元から取得できる。

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
