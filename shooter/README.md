# STAR MASTERS

enchant.js 製の 8bit 風・縦スクロールシューティング。
全3ステージ、各ステージの最後にボス。3体倒すとエンディング(スタッフロール)。

## 遊び方

ES Modules や fetch を使うため、ローカルサーバー経由で開く:

```sh
cd shooter
python3 -m http.server 8123
# → http://localhost:8123/ をブラウザで開く
```

| 操作 | キー |
|---|---|
| 移動 | 矢印キー / WASD |
| ショット | Z / Space(押しっぱなしで連射) |
| ポーズ | P |
| ミュート | M |

スマホ・タッチ操作にも対応(指の少し上に自機が追従、オート連射)。

- パワーアップ `P` を取ると最大3段階までショット強化(被弾で1段階ダウン)
- 残機3。ハイスコアは localStorage に保存

## ファイル構成

```
shooter/
├── index.html
├── lib/enchant.js        … enchant.js v0.8.3(公式ソースからビルド)
├── js/
│   ├── config.js         … ゲーム設定・全ステージ定義(敵の出現テーブル・ボス)
│   ├── assets.js         … アセットマニフェスト(画像/SE/BGM のパスを一元管理)
│   ├── audio.js          … BGM/SE 再生(Web Audio API、HTML5 Audio フォールバック)
│   ├── entities.js       … 自機・敵・ボス・弾・爆発・アイテム
│   ├── scenes.js         … タイトル/ステージ/ゲームオーバー/エンディング
│   └── main.js           … 起動・キー割り当て・デバッグフック
├── assets/
│   ├── img/*.png         … ドット絵(差し替え可)
│   ├── bgm/*.wav         … BGM 6曲(差し替え可)
│   └── se/*.wav          … 効果音 8種(差し替え可)
└── tools/
    ├── generate_images.py … ドット絵を再生成するスクリプト
    └── generate_audio.py  … BGM/SE を再生成するスクリプト
```

## アセットの差し替え方

画像・音はすべて `js/assets.js` のマニフェスト経由で参照している。

- **同じサイズの PNG / 任意の WAV に置き換えるだけ**でゲームコードの変更は不要
- パスやファイル名を変えたい場合も `js/assets.js` の該当行を書き換えるだけ
- 画像はコマを横に並べたスプライトシート。1コマのサイズ(fw/fh)とコマ数(frames)は
  `js/assets.js` に書いてあるとおりに合わせること
- 生成し直したいときは `python3 tools/generate_images.py` / `python3 tools/generate_audio.py`

## ゲーム調整

難易度・ステージ構成は `js/config.js` だけで完結:

- `STAGES[n].waves` … 敵の出現テーブル(出現時刻・種類・数・移動パターン・弾)
- `STAGES[n].boss` … ボスの HP・スコア
- `PLAYER` … 自機速度・連射間隔・残機・当たり判定

## デバッグモード

`http://localhost:8123/?debug=1` で開くと:

| キー | 効果 |
|---|---|
| 1 / 2 / 3 | 各ステージへ即ジャンプ |
| B | ボス戦へスキップ |
| K | ボス即撃破 |
| G | 無敵化 |

コンソールからも `__dbg.stage(0)` / `__dbg.boss()` / `__dbg.kill()` / `__dbg.god()` が使える。
