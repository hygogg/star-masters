/*
 * game.h — ゲーム全体の定数・型・API
 *
 * Web版(enchant.js, 320x480)からの移植。
 * DSは1画面 256x192 なので、上下2画面を縦に連結して
 * 256x384 の縦長プレイフィールドとして扱う。
 *   プレイフィールド y   0..191 → 上画面(メインエンジン)
 *   プレイフィールド y 192..383 → 下画面(サブエンジン)
 *
 * 元の 320x480 と 256x384 は縦横比が同じ(1:1.5)なので、
 * 長さ・速度をすべて x0.8 するだけでゲームバランスがそのまま移る。
 * スプライトはドット絵の原寸(Web版は2倍拡大していた)を使うため x0.5。
 */
#ifndef GAME_H
#define GAME_H

#include <nds.h>

/* ---------- 画面 ---------- */
#define SCR_W        256
#define SCR_H        192
#define FIELD_W      256
#define FIELD_H      384          /* = SCR_H * 2 */

/* ---------- 固定小数点 (24.8) ---------- */
#define FXSHIFT      8
#define FXONE        (1 << FXSHIFT)
/* 定数式でのみ使う。コンパイル時に整数へ畳み込まれる */
#define FP(f)        ((s32)((f) * 256.0f + ((f) < 0 ? -0.5f : 0.5f)))
#define FX2I(v)      ((s32)(v) >> FXSHIFT)
#define I2FX(v)      ((s32)(v) << FXSHIFT)

/* ---------- 角度 (libnds: 32768 = 1周, sinLerp は 4.12 固定小数) ---------- */
#define ANG_FULL     32768
#define ANG_DEG(d)   ((s16)((d) * 32768 / 360))
/* ラジアン指定を libnds 角度へ (定数式用) */
#define ANG_RAD(r)   ((s16)((r) * (32768.0f / 6.283185307f)))

/* ---------- 自機 ---------- */
#define PLAYER_SPEED      FP(2.72)   /* Web 3.4 * 0.8 */
#define PLAYER_SHOT_INTV  6
#define PLAYER_HIT_R      2          /* 見た目より小さい当たり判定 */
#define PLAYER_LIVES      3
#define PLAYER_RESPAWN_INV 150
#define PLAYER_MAX_POWER  3

/* ---------- 弾 ---------- */
#define PBULLET_SPEED     FP(8.0)    /* Web 10 * 0.8 */
#define EBULLET_SPEED     FP(2.08)   /* Web 2.6 * 0.8 */

/*
 * ---------- 同時表示数の上限 ----------
 * DSのハードウェア制限: スプライトは1画面(1エンジン)あたり128個まで。
 * 最悪ケース(全オブジェクトが片方の画面に集中)でも
 *   1(自機) + 1(ボス) + 24(敵) + 80(敵弾) + 32(自弾) ... は超えるため、
 * 描画は優先度順(自機→ボス→敵→敵弾→自弾→アイテム→爆発)に行い、
 * 128に達したら以降を捨てる。下記の上限は実プレイで128に達しない値。
 */
#define MAX_ENEMIES    24
#define MAX_EBULLETS   80
#define MAX_PBULLETS   28
#define MAX_ITEMS       4
#define MAX_EFFECTS    12
#define OAM_LIMIT     128

/* 敵弾が多すぎるときボスの追加発射を抑制する閾値 (Web版は140) */
#define EBULLET_CHOKE  64

/* ---------- 中ボス ----------
 * Web版 js/config.js の MIDBOSS を移植。
 *   長さ(画面上の距離) は x0.8、
 *   パーツの合体位置はスプライト同士の噛み合わせなので x0.5。
 */
#define MB_HP             8          /* 破壊に必要な被弾数(合体前・合体後とも) */
#define MB_HOLD_FRAMES   60          /* パーツ出現後の静止(1秒)。この間は無敵 */
#define MB_MERGE_FRAMES  60          /* 移動開始から合体まで(1秒)。ボーナスの猶予 */
#define MB_CORE_CY      120          /* コアが止まる中心y (Web 150 * 0.8) */
#define MB_RING_R        64          /* 静止中のパーツ位置 (Web 80 * 0.8) */
#define MB_ATTACH_R      12          /* 合体後のパーツ位置 (Web 24 * 0.5) */
#define MB_BONUS_SCORE 50000
#define MB_NORMAL_SCORE 1000
#define MB_FULL_TIMEOUT 1200         /* 倒せないと去る(進行不能の防止) */
#define MB_SHOOT_EVERY   50
#define MB_ENTER_SPEED   FP(1.28)    /* Web 1.6 * 0.8 */

/* ---------- 敵の移動パターン ---------- */
typedef enum {
    PAT_STRAIGHT = 0,
    PAT_SINE,
    PAT_SWOOP_L,
    PAT_SWOOP_R,
    PAT_HOVER,
    PAT_GROUND        /* 地上物: 背景と同じ速度で流れる */
} Pattern;

/* ---------- スプライト種別 (gfx.c の spr_defs[] と順序を一致させる) ---------- */
typedef enum {
    SPR_PLAYER = 0,
    SPR_ENEMY1,
    SPR_ENEMY2,
    SPR_ENEMY3,
    SPR_MIDENEMY,
    SPR_GTURRET,      /* 地上物: 砲台 */
    SPR_GRADAR,       /* 地上物: レーダー */
    SPR_MIDCORE,      /* 中ボス: コア */
    SPR_MIDPART,      /* 中ボス: 合体パーツ */
    SPR_BOSS1,
    SPR_BOSS2,
    SPR_BOSS3,
    SPR_BULLET_P,
    SPR_BULLET_E,
    SPR_EXPLOSION,
    SPR_POWERUP,
    SPR_COUNT
} SprId;

/* ---------- エンティティ ---------- */
typedef struct {
    s32  x, y;              /* 左上座標 (24.8) */
    bool alive;
    int  cooldown;
    int  invincible;
    int  t;
    bool touching;          /* タッチ操作中 */
    s32  touchX, touchY;
} Player;

typedef struct {
    bool active;
    s32  x, y, vx, vy;
    u8   r;                 /* 当たり判定半径(px) */
} Bullet;

typedef struct {
    bool active;
    s32  x, y, vx, vy;
    s32  baseX;             /* sine/hover の中心x (24.8, スプライト中心) */
    u8   spr;
    u8   hp;
    u16  score;
    u8   pattern;
    s32  speed;
    int  t;
    u16  shootEvery, shootTimer;
    bool drop;
    u8   flash;
    u8   r;
} Enemy;

typedef enum { BOSS_ENTER = 0, BOSS_FIGHT, BOSS_DYING } BossState;

typedef struct {
    bool active;
    s32  x, y;
    int  hp, maxHp;
    u8   state;
    int  fightAge, dyingAge;
    s16  spiralAngle;
    u8   flash;
    u8   spr;
    u8   id;                /* 1..3 */
    int  w, h;
    u8   r;
} Boss;

typedef struct {
    bool active;
    s32  x, y;
    int  t;
} Effect;                   /* 爆発 */

/* ---------- 中ボス ---------- */
typedef enum {
    MB_ENTER = 0,   /* コアが降下 (無敵) */
    MB_HOLD,        /* 四方にパーツが出現して静止 (無敵) */
    MB_MERGE,       /* パーツがコアへ集まる (有効・ここで壊すとボーナス) */
    MB_FULL,        /* 合体完了 (有効) */
    MB_DYING
} MidBossState;

typedef enum { MBR_NONE = 0, MBR_BONUS, MBR_NORMAL, MBR_ESCAPED } MidBossResult;

typedef struct {
    bool active;
    u8   state;
    u8   result;
    int  t;
    int  hp;
    s32  cx, cy;        /* コア中心 (24.8) */
    s32  partR;         /* 現在のパーツ距離 (24.8) */
    bool partsVisible;
    int  shootTimer;
    u8   flash;
} MidBoss;

typedef struct {
    bool active;
    s32  x, y;
    s32  baseX;
    int  t;
} Item;                     /* パワーアップ */

/* ---------- 進行状態 ---------- */
typedef enum {
    ST_TITLE = 0,
    ST_INTRO,
    ST_PLAY,
    ST_MIDBOSS,
    ST_WARNING,
    ST_BOSS,
    ST_CLEAR,
    ST_GAMEOVER,
    ST_ENDING
} SceneState;

/* ---------- グローバル ---------- */
typedef struct {
    u32 score, hiScore;
    int lives;
    int power;
    int stageIdx;
} GameState;

extern GameState gs;

/* ---------- API ---------- */
void game_init(void);
void game_frame(void);      /* 1フレーム進める(描画も行う) */

/* 乱数 (0..range-1) */
int  game_rand(int range);
void game_srand(u32 seed);

#endif /* GAME_H */
