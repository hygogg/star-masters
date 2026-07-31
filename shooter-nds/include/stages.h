/*
 * stages.h — ステージ定義(Web版 js/config.js の移植)
 *
 * 座標・速度はすべて Web版(320x480)の値 x0.8 = DS(256x384)。
 * 難易度調整はこのテーブルだけで完結する。
 */
#ifndef STAGES_H
#define STAGES_H

#include "game.h"

#define X_RANDOM  (-32768)      /* 出現x をランダムにする印 */

typedef struct {
    int      t;          /* 出現開始フレーム */
    u8       spr;        /* SprId */
    u8       pattern;    /* Pattern */
    u8       n;          /* 出現数 */
    u8       interval;   /* 出現間隔(フレーム) */
    s16      x;          /* 出現x(スプライト中心, px) or X_RANDOM */
    u8       hp;
    s32      speed;      /* 24.8 px/frame */
    u16      score;
    u16      shootEvery; /* 0 = 撃たない */
    bool     drop;       /* 編隊最後の1機がパワーアップを落とす */
} Wave;

typedef struct {
    const char *name;
    const char *subtitle;
    u8          bg;          /* bg_data[] のindex 0..2 */
    u8          bgm;         /* sound.h の BGM_* */
    s32         scroll;      /* 24.8 px/frame */
    const Wave *waves;
    u8          waveCount;
    int         bossAt;
    u8          bossId;      /* 1..3 (弾幕パターンの分岐に使う) */
    u8          bossSpr;
    const char *bossName;
    u16         bossHp;
    u32         bossScore;
} Stage;

#define STAGE_COUNT 3
extern const Stage stages[STAGE_COUNT];

#endif /* STAGES_H */
