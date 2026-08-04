/*
 * game.c — ゲーム本体(Web版 js/entities.js + js/scenes.js の移植)
 *
 * 進行: タイトル → STAGE1 → BOSS → STAGE2 → BOSS → STAGE3 → BOSS → エンディング
 *
 * 移植の方針:
 *   - 座標・速度は Web版(320x480)の値をすべて x0.8 して DS(256x384)へ。
 *     縦横比が同じなのでゲームバランスはそのまま移る。
 *   - 三角関数は libnds の sinLerp/cosLerp(1周=32768, 戻り値 4.12固定小数)。
 *     Web の「ラジアン毎フレーム」係数は x(32768/2π)=x5215.2 して変換した。
 *   - 各エンティティの経過時間は自前カウンタ t で持つ(ポーズで正しく止まる)。
 */
#include <stdio.h>
#include <string.h>
#include "game.h"
#include "gfx.h"
#include "sound.h"
#include "stages.h"

/*
 * 動作確認用ビルド(製品ROMではどちらも未定義。すべて 0 に畳み込まれる)。
 *
 *   make CFLAGS_EXTRA=-DTEST_FAST
 *     ボス出現までが短く、ボスHPも少ない。無敵・自動連射・ボスへの自動照準・
 *     タイトル自動開始。タイトル→3ステージ→各ボス→エンディングを数分で通せる。
 *
 *   make CFLAGS_EXTRA=-DTEST_INPUT
 *     ボタン入力を台本化して差し替える(左→右→上→下を繰り返す)。
 *     自機の移動・画面端でのクランプ・ショットが正しいかを画面で確認するため。
 */
/*
 * TEST_MB_COUNT: 中ボスの合体猶予中にコアへ何発当てられるかを実測する。
 *   コアのHPを事実上無限にして命中数を数え、HUDに出す。
 *   自機は TEST_MB_DX / TEST_MB_Y で指定した位置に固定する
 *   (ブラウザ版 tools/measure_midboss.js と同じ考え方)。
 */
#ifdef TEST_MB_COUNT
  #undef MB_HP_MERGE
  #define MB_HP_MERGE 9999
  #define TEST_MB_POS 1
static int mbHitCount;
#endif

/* TEST_MB_POS: 中ボスが居る間、自機を指定位置に固定する(実測・検証用) */
#ifdef TEST_MB_POS
  #ifndef TEST_MB_DX
    #define TEST_MB_DX 13        /* 実測での最良位置 */
  #endif
  #ifndef TEST_MB_Y
    #define TEST_MB_Y 160
  #endif
#endif

#if defined(TEST_GROUND)
  /* 地上物の確認用: 中ボスを出さず、ステージを通常どおり流す */
  #define MIDBOSS_AT(s) 0
  #define BOSS_AT(s)   3000
  #define BOSS_HP(s)   40
  #define T_AUTOSTART  1
  #define T_INVINC     1
#elif defined(TEST_FAST) || defined(TEST_INPUT)
  #define MIDBOSS_AT(s) 120           /* 中ボスも早く出す */
  #define BOSS_AT(s)   480
  #define BOSS_HP(s)   40
  #define T_AUTOSTART  1
  #define T_INVINC     1
#else
  #define MIDBOSS_AT(s) ((s)->midBossAt)
  #define BOSS_AT(s)   ((s)->bossAt)
  #define BOSS_HP(s)   ((s)->bossHp)
  #define T_AUTOSTART  0
  #define T_INVINC     0
#endif

/*
 * TEST_MB_LETMERGE: 中ボスが合体するまで自動連射を止める。
 * 合体後の通常形態(1000点側)を画面で確認するためのテスト専用。
 */
#ifdef TEST_MB_LETMERGE
  #define T_HOLD_FIRE (midBoss.active && midBoss.state != MB_FULL)
#else
  #define T_HOLD_FIRE 0
#endif

#ifdef TEST_FAST
  #define T_AUTOFIRE 1
  #define T_AUTOAIM  1
#else
  #define T_AUTOFIRE 0
  #define T_AUTOAIM  0
#endif

GameState gs;

/* ---------- 乱数 (線形合同法) ---------- */
static u32 rngState = 0x12345678u;

void game_srand(u32 seed) { rngState = seed ? seed : 1u; }

int game_rand(int range)
{
    rngState = rngState * 1664525u + 1013904223u;
    if (range <= 0) return 0;
    return (int)((rngState >> 16) % (u32)range);
}

/* ---------- 固定小数の三角関数 ---------- */
/* 振幅(24.8)と libnds角度から 24.8 のオフセットを得る */
#define SINFX(ampFx, ang) (((s32)(ampFx) * sinLerp((s16)(ang))) >> 12)
#define COSFX(ampFx, ang) (((s32)(ampFx) * cosLerp((s16)(ang))) >> 12)

/* ラジアン毎フレーム → libnds角度毎フレーム */
#define RATE_SINE_ENEMY   287   /* 0.055 rad */
#define RATE_HOVER        157   /* 0.030 rad */
#define RATE_ITEM         261   /* 0.050 rad */
#define RATE_B1_X         104   /* 0.020 rad */
#define RATE_B1_Y          68   /* 0.013 rad */
#define RATE_B2_X         172   /* 0.033 rad */
#define RATE_B2_Y         110   /* 0.021 rad */
#define RATE_B3_X          63   /* 0.012 rad */
#define RATE_B3_Y          89   /* 0.017 rad */

/* 拡散角(ラジアン → libnds角度) */
#define SPREAD_026       1356
#define SPREAD_024       1252
#define SPREAD_030       1565
#define SPREAD_022       1147
#define SPREAD_020       1043
/* 螺弾の1発ごとの角度増分 */
#define SPIRAL_023       1200
#define SPIRAL_031       1617
#define SPIRAL_029       1512

/* ---------- エンティティ ---------- */
static Player player;
static Enemy  enemies[MAX_ENEMIES];
static Bullet ebullets[MAX_EBULLETS];
static Bullet pbullets[MAX_PBULLETS];
static Item   items[MAX_ITEMS];
static Effect effects[MAX_EFFECTS];
static Boss   boss;
static MidBoss midBoss;

static int  enemyCount;      /* 生存数(WARNING判定用) */
static int  ebulletCount;

/* ---------- 進行状態 ---------- */
static int  state;
static int  stateTimer;
static int  stageIdx;
static int  stageT;          /* ステージ経過フレーム */
static int  deathTimer;
static int  gameOverTimer;
static s32  scrollAccum;        /* 背景スクロール累積 (24.8) */
static bool paused;
static bool midBossDone;      /* このステージの中ボスを消化したか */
static int  midBossMsg;       /* ボーナス表示の残りフレーム */
static int  frameCounter;    /* 演出の点滅用 */

/* 実行中の編隊 */
typedef struct {
    const Wave *wave;
    int spawned;
    int timer;
    bool active;
} Spawner;
#define MAX_SPAWNERS 6
static Spawner spawners[MAX_SPAWNERS];
static int nextWave;         /* まだ開始していない wave のindex */

/* タイトル/エンディング用 */
static bool titleArmed;      /* ボタンを一度離したか */
static s32  endShipY;
static s32  creditScroll;
static bool creditsDone;

static const Stage *stg;     /* 現ステージ */

/* ============================================================ */
/* 小物                                                          */
/* ============================================================ */

/*
 * 入力の取得口。TEST_INPUT ビルドでは台本に差し替える。
 * (製品ビルドでは keysHeld() を呼ぶだけにコンパイルされる)
 */
#ifdef TEST_INPUT
static int held_keys(void)
{
    int t = frameCounter % 540;
    int k = KEY_A;                       /* 常時ショット */
    if      (t < 150) k |= KEY_LEFT;     /* 左端まで寄る */
    else if (t < 300) k |= KEY_RIGHT;    /* 右端まで寄る */
    else if (t < 390) k |= KEY_UP;       /* 上端(HUD下)まで */
    else if (t < 480) k |= KEY_DOWN;     /* 下端まで */
    return k;
}
#else
static inline int held_keys(void) { return keysHeld(); }
#endif

static inline int keysShot(void)  { return held_keys() & (KEY_A | KEY_B | KEY_X | KEY_Y); }

static inline int cx_of(s32 x, int id) { return FX2I(x) + spr_w(id) / 2; }
static inline int cy_of(s32 y, int id) { return FX2I(y) + spr_h(id) / 2; }

static void clear_center_msg(void);   /* 定義は描画セクション */

static bool hit_circle(int ax, int ay, int ar, int bx, int by, int br)
{
    int dx = ax - bx, dy = ay - by, r = ar + br;
    return dx * dx + dy * dy < r * r;
}

/* ============================================================ */
/* 生成                                                          */
/* ============================================================ */

static void add_effect(int cx, int cy)
{
    int i;
    for (i = 0; i < MAX_EFFECTS; i++) {
        if (!effects[i].active) {
            effects[i].active = true;
            effects[i].x = I2FX(cx - spr_w(SPR_EXPLOSION) / 2);
            effects[i].y = I2FX(cy - spr_h(SPR_EXPLOSION) / 2);
            effects[i].t = 0;
            return;
        }
    }
}

static void add_item(int cx, int cy)
{
    int i;
    for (i = 0; i < MAX_ITEMS; i++) {
        if (!items[i].active) {
            items[i].active = true;
            items[i].baseX = I2FX(cx);
            items[i].x = I2FX(cx - spr_w(SPR_POWERUP) / 2);
            items[i].y = I2FX(cy - spr_h(SPR_POWERUP) / 2);
            items[i].t = 0;
            return;
        }
    }
}

static void add_pbullet(int cx, int cy, s32 vx)
{
    int i;
    for (i = 0; i < MAX_PBULLETS; i++) {
        if (!pbullets[i].active) {
            pbullets[i].active = true;
            pbullets[i].x = I2FX(cx - spr_w(SPR_BULLET_P) / 2);
            pbullets[i].y = I2FX(cy - spr_h(SPR_BULLET_P) / 2);
            pbullets[i].vx = vx;
            pbullets[i].vy = -PBULLET_SPEED;
            pbullets[i].r = 3;
            return;
        }
    }
}

static void add_ebullet(int cx, int cy, s16 ang, s32 speed)
{
    int i;
    if (ebulletCount >= MAX_EBULLETS) return;
    for (i = 0; i < MAX_EBULLETS; i++) {
        if (!ebullets[i].active) {
            ebullets[i].active = true;
            ebullets[i].x = I2FX(cx - spr_w(SPR_BULLET_E) / 2);
            ebullets[i].y = I2FX(cy - spr_h(SPR_BULLET_E) / 2);
            ebullets[i].vx = COSFX(speed, ang);
            ebullets[i].vy = SINFX(speed, ang);
            ebullets[i].r = 2;
            ebulletCount++;
            return;
        }
    }
}

/* 自機へ向かう角度(libnds角度)。自機が居なければ真下(=90度) */
static s16 angle_to_player(int fromX, int fromY)
{
    int dx, dy, len, u;
    s16 a;
    if (!player.alive) return ANG_DEG(90);
    dx = cx_of(player.x, SPR_PLAYER) - fromX;
    dy = cy_of(player.y, SPR_PLAYER) - fromY;
    len = (int)sqrt32(dx * dx + dy * dy);
    if (len <= 0) return ANG_DEG(90);
    u = (dx * 4096) / len;                 /* cos成分を 4.12 で */
    if (u > 4096) u = 4096;
    if (u < -4096) u = -4096;
    a = acosLerp((s16)u);                  /* 0..16384 (0..180度) */
    return (dy < 0) ? (s16)(-a) : a;       /* 下向き(dy>0)はそのまま */
}

static void fire_aimed(int x, int y, int count, s16 spread, s32 speed)
{
    s16 base = angle_to_player(x, y);
    s16 start = (s16)(base - spread * (count - 1) / 2);
    int i;
    for (i = 0; i < count; i++)
        add_ebullet(x, y, (s16)(start + spread * i), speed);
}

static void fire_ring(int x, int y, int count, s32 speed, s16 offset)
{
    int i;
    for (i = 0; i < count; i++)
        add_ebullet(x, y, (s16)(offset + (s32)i * ANG_FULL / count), speed);
}

/* ============================================================ */
/* 自機                                                          */
/* ============================================================ */

static void player_reset(void)
{
    player.x = I2FX(FIELD_W / 2 - spr_w(SPR_PLAYER) / 2);
    player.y = I2FX(FIELD_H - 40 - spr_h(SPR_PLAYER) / 2);
    player.alive = true;
    player.cooldown = 0;
    player.invincible = PLAYER_RESPAWN_INV;
    player.t = 0;
    player.touching = false;
}

static void player_shoot(void)
{
    int cx = cx_of(player.x, SPR_PLAYER);
    int top = FX2I(player.y) + 2;

    /*
     * 発射位置のオフセットは「自機のどこから出るか」なのでスプライト基準 = x0.5。
     * (Web版 ±11/±14 → ±6/±7。以前は他の距離と同じ x0.8 にしていたため、
     *  16px の自機の外側から弾が出ていた)
     * 斜め弾の vx は画面上の速度なので従来どおり x0.8。
     */
    add_pbullet(cx, top, 0);
    if (gs.power >= 2) {
        add_pbullet(cx - 6, top + 3, 0);
        add_pbullet(cx + 6, top + 3, 0);
    }
    if (gs.power >= 3) {
        add_pbullet(cx - 7, top + 5, -FP(1.44));
        add_pbullet(cx + 7, top + 5,  FP(1.44));
    }
    snd_se(SE_SHOT);
}

static void player_update(void)
{
    int held = held_keys();
    int w = spr_w(SPR_PLAYER), h = spr_h(SPR_PLAYER);
    s32 maxX = I2FX(FIELD_W - w);
    s32 minY = I2FX(28);                 /* HUD の下 */
    s32 maxY = I2FX(FIELD_H - h);

    if (!player.alive) return;
    player.t++;

    if (held & KEY_LEFT)  player.x -= PLAYER_SPEED;
    if (held & KEY_RIGHT) player.x += PLAYER_SPEED;
    if (held & KEY_UP)    player.y -= PLAYER_SPEED;
    if (held & KEY_DOWN)  player.y += PLAYER_SPEED;

    /* タッチ操作: 指の少し上へ追従(下画面のみ有効) */
    if (held & KEY_TOUCH) {
        touchPosition tp;
        touchRead(&tp);
        if (tp.px || tp.py) {
            s32 tx, ty, d;
            player.touching = true;
            tx = I2FX(tp.px - w / 2);
            ty = I2FX(tp.py + SCR_H - 32 - h / 2);   /* 下画面 → フィールド座標 */
            d = tx - player.x;
            if (d >  FP(5)) d =  FP(5);
            if (d < -FP(5)) d = -FP(5);
            player.x += d;
            d = ty - player.y;
            if (d >  FP(5)) d =  FP(5);
            if (d < -FP(5)) d = -FP(5);
            player.y += d;
        }
    } else {
        player.touching = false;
    }

#ifdef TEST_MB_POS
    /* 測定・検証用: 中ボスが居る間は指定位置に固定して撃ちっぱなし */
    if (midBoss.active) {
        player.x = midBoss.cx + I2FX(TEST_MB_DX) - I2FX(w / 2);
        player.y = I2FX(TEST_MB_Y);
    }
#endif
    /* 動作確認ビルド: ボスに自動で照準を合わせる(確実に進行させるため) */
    if (T_AUTOAIM && boss.active) {
        s32 target = boss.x + I2FX(boss.w / 2) - I2FX(w / 2);
        if (player.x < target - PLAYER_SPEED)      player.x += PLAYER_SPEED;
        else if (player.x > target + PLAYER_SPEED) player.x -= PLAYER_SPEED;
    }

    if (player.x < 0) player.x = 0;
    if (player.x > maxX) player.x = maxX;
    if (player.y < minY) player.y = minY;
    if (player.y > maxY) player.y = maxY;

    if (player.cooldown > 0) player.cooldown--;
    if ((keysShot() || player.touching || (T_AUTOFIRE && !T_HOLD_FIRE)) &&
        player.cooldown <= 0) {
        player_shoot();
        player.cooldown = PLAYER_SHOT_INTV;
    }

    if (T_INVINC) player.invincible = 2;      /* 動作確認ビルドは無敵 */
    else if (player.invincible > 0) player.invincible--;
}

static void kill_player(void)
{
    if (!player.alive || player.invincible > 0) return;
    player.alive = false;
    player.touching = false;
    add_effect(cx_of(player.x, SPR_PLAYER), cy_of(player.y, SPR_PLAYER));
    snd_se(SE_PLAYER_DEATH);
    gs.lives--;
    if (gs.lives < 0) gameOverTimer = 100;
    else               deathTimer = 70;
}

static void respawn(void)
{
    if (gs.power > 1) gs.power--;
    player_reset();
}

/* ============================================================ */
/* 敵                                                            */
/* ============================================================ */

static void spawn_enemy(const Wave *w, int baseXpx, bool drop)
{
    int i;
    for (i = 0; i < MAX_ENEMIES; i++) {
        Enemy *e = &enemies[i];
        if (e->active) continue;
        e->active = true;
        e->spr = w->spr;
        e->pattern = w->pattern;
        e->hp = w->hp;
        e->score = w->score;
        e->speed = w->speed;
        e->baseX = I2FX(baseXpx);
        e->x = I2FX(baseXpx - spr_w(w->spr) / 2);
        e->y = I2FX(-spr_h(w->spr));
        e->vx = 0;
        e->vy = w->speed;
        e->t = 0;
        e->drop = drop;
        e->flash = 0;
        /*
         * 当たり判定。DSではドット絵が原寸(Web版の半分)なので、
         * Web版の係数(0.36)そのままだと当たり判定が小さすぎて撃ちにくい。
         * スプライトからはみ出さない範囲で少し大きめの 0.45 にしている。
         */
        e->r = (u8)(spr_w(w->spr) * 45 / 100);
        e->shootEvery = w->shootEvery;
        e->shootTimer = w->shootEvery ? (u16)(20 + game_rand(w->shootEvery)) : 0;

        if (w->pattern == PAT_SWOOP_L) { e->vx =  FP(0.48); e->vy = w->speed * 3 / 2; }
        if (w->pattern == PAT_SWOOP_R) { e->vx = -FP(0.48); e->vy = w->speed * 3 / 2; }
        enemyCount++;
        return;
    }
}

static void enemy_kill(Enemy *e, bool byBullet)
{
    int cx = cx_of(e->x, e->spr), cy = cy_of(e->y, e->spr);
    add_effect(cx, cy);
    if (byBullet) {
        snd_se(SE_EXPLOSION);
        gs.score += e->score;
        if (gs.score > gs.hiScore) gs.hiScore = gs.score;
        if (e->drop) add_item(cx, cy);
    }
    e->active = false;
    enemyCount--;
}

static void enemy_update(Enemy *e)
{
    int w = spr_w(e->spr), h = spr_h(e->spr);
    int t = ++e->t;

    switch (e->pattern) {
    case PAT_SINE:
        e->y += e->speed * 217 / 256;                  /* x0.85 */
        e->x = e->baseX - I2FX(w / 2) + SINFX(FP(36.8), t * RATE_SINE_ENEMY);
        break;
    case PAT_SWOOP_L:
        if (t > 40) {
            e->vx += FP(0.096);
            e->vy -= FP(0.04);
            if (e->vy < FP(0.48)) e->vy = FP(0.48);
        }
        e->x += e->vx; e->y += e->vy;
        break;
    case PAT_SWOOP_R:
        if (t > 40) {
            e->vx -= FP(0.096);
            e->vy -= FP(0.04);
            if (e->vy < FP(0.48)) e->vy = FP(0.48);
        }
        e->x += e->vx; e->y += e->vy;
        break;
    /*
     * 地上物。背景と同じ速度で流れるので「地面に固定されている」ように見える。
     * 空中物との違いは移動だけで、当たり判定・破壊のされ方は同じ
     * (通常ショットで壊せる)。
     */
    case PAT_GROUND:
        e->y += stg->scroll;
        break;
    case PAT_HOVER:
        if (FX2I(e->y) < 72) {
            e->y += e->speed;
        } else if (t < 480) {
            e->x = e->baseX - I2FX(w / 2) + SINFX(FP(19.2), t * RATE_HOVER);
        } else {
            e->y += (s32)(t - 480) * FP(0.016) + FP(0.4);
        }
        break;
    default:  /* PAT_STRAIGHT */
        e->y += e->speed;
        break;
    }

    /* 自機狙い弾 */
    if (e->shootEvery) {
        int cy = cy_of(e->y, e->spr);
        if (cy > 6 && cy < 288) {
            if (e->shootTimer > 0) e->shootTimer--;
            if (e->shootTimer == 0) {
                e->shootTimer = e->shootEvery;
                fire_aimed(cx_of(e->x, e->spr), cy + 6, 1, 0,
                           EBULLET_SPEED + e->speed * 77 / 256);   /* +speed*0.3 */
            }
        }
    }

    if (e->flash > 0) e->flash--;

    /* 画面外で消滅 */
    if (FX2I(e->y) > FIELD_H + 40 || FX2I(e->x) < -64 ||
        FX2I(e->x) > FIELD_W + 64 || FX2I(e->y) < -130) {
        e->active = false;
        enemyCount--;
    }
    (void)h;
}

/* ============================================================ */
/* ボス                                                          */
/* ============================================================ */

static void boss_start(void)
{
    boss.active = true;
    boss.spr = stg->bossSpr;
    boss.id = stg->bossId;
    boss.w = spr_w(boss.spr);
    boss.h = spr_h(boss.spr);
    boss.hp = boss.maxHp = BOSS_HP(stg);
    boss.state = BOSS_ENTER;
    boss.fightAge = 0;
    boss.dyingAge = 0;
    boss.spiralAngle = 0;
    boss.flash = 0;
    boss.r = (u8)(boss.w * 42 / 100);
    boss.x = I2FX(FIELD_W / 2 - boss.w / 2);
    boss.y = I2FX(-boss.h - 8);
}

static void boss_move(void)
{
    int t = boss.fightAge;
    s32 cx = I2FX(FIELD_W / 2 - boss.w / 2);
    switch (boss.id) {
    case 1:
        boss.x = cx + SINFX(FP(64.0), t * RATE_B1_X);
        boss.y = I2FX(32) + SINFX(FP(9.6), t * RATE_B1_Y);
        break;
    case 2:
        boss.x = cx + SINFX(FP(80.0), t * RATE_B2_X);
        boss.y = I2FX(32) + SINFX(FP(14.4), t * RATE_B2_Y);
        break;
    default:
        boss.x = cx + SINFX(FP(48.0), t * RATE_B3_X);
        boss.y = I2FX(32) + SINFX(FP(8.0), t * RATE_B3_Y);
        break;
    }
}

static void boss_attack(void)
{
    int bx, by, t, c;
    bool phase2;

    /* 敵弾が多すぎるときは追加発射を抑制(処理落ち・理不尽の防止) */
    if (ebulletCount > EBULLET_CHOKE) return;

    bx = cx_of(boss.x, boss.spr);
    by = cy_of(boss.y, boss.spr) + 16;
    t = boss.fightAge;
    phase2 = (boss.hp <= boss.maxHp / 2);

    switch (boss.id) {
    case 1:
        if (!phase2) {
            c = t % 300;
            if (c == 30 || c == 60 || c == 90) fire_aimed(bx, by, 3, SPREAD_026, FP(2.4));
            if (c == 200) fire_ring(bx, by, 16, FP(1.76), (s16)game_rand(ANG_FULL / 2));
        } else {
            c = t % 260;
            if (c == 20 || c == 50 || c == 80 || c == 110)
                fire_aimed(bx, by, 5, SPREAD_024, FP(2.56));
            if (c == 180) fire_ring(bx, by, 20, FP(2.0), (s16)game_rand(ANG_FULL / 2));
        }
        break;

    case 2: {
        int lx = FX2I(boss.x) + 10;
        int rx = FX2I(boss.x) + boss.w - 10;
        int wy = FX2I(boss.y) + 48;
        if (!phase2) {
            c = t % 240;
            if (c > 0 && c <= 100 && (c % 20) == 0) {
                fire_aimed(lx, wy, 1, 0, FP(2.64));
                fire_aimed(rx, wy, 1, 0, FP(2.64));
            }
            if (c == 160) fire_ring(bx, by, 14, FP(1.92), (s16)game_rand(ANG_FULL / 2));
        } else {
            if ((t % 6) == 0) {
                boss.spiralAngle = (s16)(boss.spiralAngle + SPIRAL_023);
                add_ebullet(bx, by, boss.spiralAngle, FP(2.08));
                add_ebullet(bx, by, (s16)(boss.spiralAngle + ANG_FULL / 2), FP(2.08));
            }
            if ((t % 70) == 0) fire_aimed(bx, by, 3, SPREAD_030, FP(2.72));
        }
        break;
    }

    default:
        if (!phase2) {
            c = t % 330;
            if (c == 30) fire_ring(bx, by, 20, FP(1.84), 0);
            if (c >= 90 && c <= 180 && (c % 8) == 0) {
                boss.spiralAngle = (s16)(boss.spiralAngle + SPIRAL_031);
                add_ebullet(bx, by, boss.spiralAngle, FP(2.0));
            }
            if (c == 240 || c == 270) fire_aimed(bx, by, 5, SPREAD_022, FP(2.56));
        } else {
            c = t % 300;
            /* Web版は24発リングだが、DSはスプライト128個/画面の制限があるため20発に */
            if (c == 20) fire_ring(bx, by, 20, FP(1.92), 0);
            if (c == 90) fire_ring(bx, by, 20, FP(1.92), (s16)(ANG_FULL / 40));
            if (c >= 120 && c <= 240 && (c % 7) == 0) {
                boss.spiralAngle = (s16)(boss.spiralAngle + SPIRAL_029);
                add_ebullet(bx, by, boss.spiralAngle, FP(2.16));
                add_ebullet(bx, by, (s16)(boss.spiralAngle + ANG_FULL / 2), FP(2.16));
            }
            if (c == 260) fire_aimed(bx, by, 7, SPREAD_020, FP(2.72));
        }
        break;
    }
}

/* 中ボスを倒したときの加点と演出 */
static void on_midboss_hit(int result)
{
    if (result == MBR_BONUS) {
        gs.score += MB_BONUS_SCORE;
        if (gs.score > gs.hiScore) gs.hiScore = gs.score;
        midBossMsg = 150;
    } else if (result == MBR_NORMAL) {
        gs.score += MB_NORMAL_SCORE;
        if (gs.score > gs.hiScore) gs.hiScore = gs.score;
    }
}

static void clear_ebullets(void)
{
    int i;
    for (i = 0; i < MAX_EBULLETS; i++) ebullets[i].active = false;
    ebulletCount = 0;
}

static void on_boss_dead(void)
{
    boss.active = false;
    gs.score += stg->bossScore;
    if (gs.score > gs.hiScore) gs.hiScore = gs.score;
    snd_bgm_stop();
    snd_se(SE_CLEAR);
    state = ST_CLEAR;
    stateTimer = 240;
    clear_ebullets();
}

static void boss_update(void)
{
    if (boss.state == BOSS_ENTER) {
        boss.y += FP(0.96);
        if (FX2I(boss.y) >= 32) boss.state = BOSS_FIGHT;
    } else if (boss.state == BOSS_FIGHT) {
        boss.fightAge++;
        boss_move();
        boss_attack();
    } else {
        boss.dyingAge++;
        boss.x += I2FX(game_rand(5) - 2);
        if ((boss.dyingAge % 8) == 0) {
            add_effect(cx_of(boss.x, boss.spr) + game_rand(64) - 32,
                       cy_of(boss.y, boss.spr) + game_rand(64) - 32);
            snd_se(SE_EXPLOSION);
        }
        if (boss.dyingAge >= 110) { on_boss_dead(); return; }
    }
    if (boss.flash > 0) boss.flash--;
}

static void boss_damage(int n)
{
    if (boss.state != BOSS_FIGHT) return;
    boss.hp -= n;
    boss.flash = 3;
    snd_se(SE_HIT);
    if (boss.hp <= 0) {
        boss.hp = 0;
        boss.state = BOSS_DYING;
        boss.dyingAge = 0;
        snd_se(SE_BOSS_EXPLOSION);
    }
}

/* ============================================================ */
/* 中ボス                                                        */
/* ============================================================ */

/*
 * コア1つ + 四方(上下左右)のパーツ4つ。Web版と同じ流れ:
 *   ENTER … コアが上部へ降下                (無敵)
 *   HOLD  … 四方にパーツが出現して静止       (無敵) MB_HOLD_FRAMES
 *   MERGE … パーツがコアへ集まる             (有効) MB_MERGE_FRAMES
 *           ここで MB_HP 発当てて壊すと MB_BONUS_SCORE + ファンファーレ
 *   FULL  … 合体完了。HPを戻して通常戦闘      (有効) 壊すと MB_NORMAL_SCORE
 * 当たり判定はコアと4パーツそれぞれに持たせ、ダメージは1つのHPに集約する。
 */
static const s8 MB_DIRS[4][2] = { { 0, -1 }, { 0, 1 }, { -1, 0 }, { 1, 0 } };

static void midboss_start(void)
{
    memset(&midBoss, 0, sizeof(midBoss));
    midBoss.active = true;
    midBoss.state = MB_ENTER;
    midBoss.result = MBR_NONE;
    midBoss.hp = MB_HP_MERGE;
    midBoss.cx = I2FX(FIELD_W / 2);
    midBoss.cy = -I2FX(spr_h(SPR_MIDCORE) / 2);
}

/* 画面外の出現位置(コア中心からの距離)を確定させる */
static void midboss_set_starts(void)
{
    int pw = spr_w(SPR_MIDPART), ph = spr_h(SPR_MIDPART);
    midBoss.startDist[0] = midBoss.cy + I2FX(ph / 2);                      /* 上の外 */
    midBoss.startDist[1] = I2FX(FIELD_H + ph / 2) - midBoss.cy;            /* 下の外 */
    midBoss.startDist[2] = midBoss.cx + I2FX(pw / 2);                      /* 左の外 */
    midBoss.startDist[3] = I2FX(FIELD_W + pw / 2) - midBoss.cx;            /* 右の外 */
}

static void midboss_set_dist(s32 d)
{
    int i;
    for (i = 0; i < 4; i++) midBoss.partDist[i] = d;
}

/* コアに攻撃が通る状態か(パーツの移動開始前は効かない) */
static bool midboss_core_vulnerable(void)
{
    return midBoss.active &&
           (midBoss.state == MB_MERGE || midBoss.state == MB_FULL);
}

/* パーツ i の中心座標 */
static void midboss_part_pos(int i, int *px, int *py)
{
    int d = FX2I(midBoss.partDist[i]);
    *px = FX2I(midBoss.cx) + MB_DIRS[i][0] * d;
    *py = FX2I(midBoss.cy) + MB_DIRS[i][1] * d;
}

/* コアの当たり判定 */
static void midboss_core_target(int *tx, int *ty, int *tr)
{
    *tx = FX2I(midBoss.cx);
    *ty = FX2I(midBoss.cy);
    *tr = spr_w(SPR_MIDCORE) * 36 / 100;
}

/* 戻り値: 撃破したら MBR_BONUS / MBR_NORMAL、まだなら MBR_NONE */
static int midboss_damage(int n)
{
    if (!midboss_core_vulnerable()) return MBR_NONE;
#ifdef TEST_MB_COUNT
    if (midBoss.state == MB_MERGE) mbHitCount++;
#endif
    midBoss.hp -= n;
    midBoss.flash = 3;
    if (midBoss.hp > 0) {
        snd_se(SE_HIT);
        return MBR_NONE;
    }
    midBoss.hp = 0;
    midBoss.result = (midBoss.state == MB_MERGE) ? MBR_BONUS : MBR_NORMAL;
    midBoss.state = MB_DYING;
    midBoss.t = 0;
    snd_se(midBoss.result == MBR_BONUS ? SE_FANFARE : SE_BOSS_EXPLOSION);
    return midBoss.result;
}

/* 戻り値: false で消滅(呼び出し側が後処理する) */
static bool midboss_update(void)
{
    int t = ++midBoss.t;
    int i;

    switch (midBoss.state) {
    case MB_ENTER:
        midBoss.cy += MB_ENTER_SPEED;
        if (FX2I(midBoss.cy) >= MB_CORE_CY) {
            midBoss.cy = I2FX(MB_CORE_CY);
            midBoss.state = MB_FLYIN;
            midBoss.t = 0;
            midBoss.partsVisible = true;
            midboss_set_starts();
            for (i = 0; i < 4; i++) midBoss.partDist[i] = midBoss.startDist[i];
        }
        break;

    case MB_FLYIN: {
        /* 四方の画面外から静止位置へ。この間は当たり判定なし */
        s32 k = (t > MB_FLYIN_FRAMES) ? MB_FLYIN_FRAMES : t;
        for (i = 0; i < 4; i++) {
            s32 a = midBoss.startDist[i], b = I2FX(MB_RING_R);
            midBoss.partDist[i] = a + (b - a) * k / MB_FLYIN_FRAMES;
        }
        if (t >= MB_FLYIN_FRAMES) {
            midboss_set_dist(I2FX(MB_RING_R));
            midBoss.state = MB_HOLD;
            midBoss.t = 0;
            midBoss.partsSolid = true;      /* ここから障害物になる */
        }
        break;
    }

    case MB_HOLD:
        if (t >= MB_HOLD_FRAMES) { midBoss.state = MB_MERGE; midBoss.t = 0; }
        break;

    case MB_MERGE: {
        s32 k = (t > MB_MERGE_FRAMES) ? MB_MERGE_FRAMES : t;
        midboss_set_dist(I2FX(MB_RING_R) +
            (I2FX(MB_ATTACH_R) - I2FX(MB_RING_R)) * k / MB_MERGE_FRAMES);
        if (t >= MB_MERGE_FRAMES) {
            midBoss.state = MB_FULL;          /* 合体成立。HPを合体後の値に */
            midBoss.t = 0;
            midBoss.hp = MB_HP_FULL;
            midboss_set_dist(I2FX(MB_ATTACH_R));
            midBoss.shootTimer = 30;
        }
        break;
    }

    case MB_FULL:
        midBoss.cx = I2FX(FIELD_W / 2) + SINFX(FP(72.0), t * 130);
        midBoss.cy = I2FX(MB_CORE_CY) + SINFX(FP(11.2), t * 89);
        if (--midBoss.shootTimer <= 0) {
            midBoss.shootTimer = MB_SHOOT_EVERY;
            fire_aimed(FX2I(midBoss.cx), FX2I(midBoss.cy) + 16, 3, SPREAD_026, FP(2.4));
        }
        if (t >= MB_FULL_TIMEOUT) {           /* 倒せないままなら去る */
            midBoss.result = MBR_ESCAPED;
            midBoss.state = MB_DYING;
            midBoss.t = 0;
        }
        break;

    case MB_DYING:
        midBoss.partsSolid = false;
        if (midBoss.result == MBR_ESCAPED) {
            midBoss.cy -= FP(2.4);
            if (FX2I(midBoss.cy) < -spr_h(SPR_MIDCORE)) return false;
        } else {
            if ((t % 7) == 0) {
                add_effect(FX2I(midBoss.cx) + game_rand(64) - 32,
                           FX2I(midBoss.cy) + game_rand(64) - 32);
                /* ボーナス時はファンファーレを爆発音で潰さない */
                if (midBoss.result != MBR_BONUS) snd_se(SE_EXPLOSION);
            }
            if (t >= 80) return false;
        }
        break;
    }

    if (midBoss.flash > 0) midBoss.flash--;
    return true;
}

/* ============================================================ */
/* 弾・アイテム・爆発                                            */
/* ============================================================ */

static void bullets_update(void)
{
    int i;
    for (i = 0; i < MAX_PBULLETS; i++) {
        Bullet *b = &pbullets[i];
        if (!b->active) continue;
        b->x += b->vx;
        b->y += b->vy;
        if (FX2I(b->y) < -20 || FX2I(b->x) < -20 || FX2I(b->x) > FIELD_W + 20)
            b->active = false;
    }
    for (i = 0; i < MAX_EBULLETS; i++) {
        Bullet *b = &ebullets[i];
        if (!b->active) continue;
        b->x += b->vx;
        b->y += b->vy;
        if (FX2I(b->y) < -20 || FX2I(b->y) > FIELD_H + 20 ||
            FX2I(b->x) < -20 || FX2I(b->x) > FIELD_W + 20) {
            b->active = false;
            ebulletCount--;
        }
    }
}

static void items_update(void)
{
    int i;
    for (i = 0; i < MAX_ITEMS; i++) {
        Item *it = &items[i];
        if (!it->active) continue;
        it->t++;
        it->y += FP(1.04);
        it->x = it->baseX - I2FX(spr_w(SPR_POWERUP) / 2)
                + SINFX(FP(12.8), it->t * RATE_ITEM);
        if (FX2I(it->y) > FIELD_H + 20) it->active = false;
    }
}

static void effects_update(void)
{
    int i;
    for (i = 0; i < MAX_EFFECTS; i++) {
        if (!effects[i].active) continue;
        if (++effects[i].t >= 20) effects[i].active = false;
    }
}

/* ============================================================ */
/* 当たり判定                                                    */
/* ============================================================ */

static void collide(void)
{
    int i, j;
    int px, py;

    /* 自機弾 vs 敵 / ボス */
    for (i = 0; i < MAX_PBULLETS; i++) {
        Bullet *b = &pbullets[i];
        int bx, by;
        if (!b->active) continue;
        bx = FX2I(b->x) + spr_w(SPR_BULLET_P) / 2;
        by = FX2I(b->y) + spr_h(SPR_BULLET_P) / 2;

        for (j = 0; j < MAX_ENEMIES; j++) {
            Enemy *e = &enemies[j];
            if (!e->active) continue;
            if (!hit_circle(bx, by, b->r, cx_of(e->x, e->spr), cy_of(e->y, e->spr), e->r))
                continue;
            b->active = false;
            e->flash = 3;
            if (--e->hp <= 0) enemy_kill(e, true);
            else              snd_se(SE_HIT);
            break;
        }
        if (!b->active) continue;

        if (boss.active && boss.state == BOSS_FIGHT &&
            hit_circle(bx, by, b->r, cx_of(boss.x, boss.spr),
                       cy_of(boss.y, boss.spr), boss.r)) {
            b->active = false;
            boss_damage(1);
            continue;
        }

        /*
         * 自機弾 vs 中ボス。
         * パーツは常に無敵の障害物なので先に判定してショットを弾く
         * (ダメージにはならない)。ダメージが通るのはコアだけ。
         */
        if (midBoss.active) {
            int k, tx, ty, tr, pr = spr_w(SPR_MIDPART) * 36 / 100;
            bool blocked = false;
            if (midBoss.partsSolid) {
                for (k = 0; k < 4; k++) {
                    midboss_part_pos(k, &tx, &ty);
                    if (!hit_circle(bx, by, b->r, tx, ty, pr)) continue;
                    b->active = false;
                    blocked = true;
                    break;
                }
            }
            if (!blocked && midboss_core_vulnerable()) {
                midboss_core_target(&tx, &ty, &tr);
                if (hit_circle(bx, by, b->r, tx, ty, tr)) {
                    b->active = false;
                    on_midboss_hit(midboss_damage(1));
                }
            }
        }
    }

    if (!player.alive) return;
    px = cx_of(player.x, SPR_PLAYER);
    py = cy_of(player.y, SPR_PLAYER);

    if (player.invincible <= 0) {
        /* 敵弾 vs 自機 */
        for (i = 0; i < MAX_EBULLETS; i++) {
            Bullet *b = &ebullets[i];
            if (!b->active) continue;
            if (hit_circle(FX2I(b->x) + spr_w(SPR_BULLET_E) / 2,
                           FX2I(b->y) + spr_h(SPR_BULLET_E) / 2, b->r,
                           px, py, PLAYER_HIT_R)) {
                b->active = false;
                ebulletCount--;
                kill_player();
                return;
            }
        }
        /* 敵本体 vs 自機 */
        for (i = 0; i < MAX_ENEMIES; i++) {
            Enemy *e = &enemies[i];
            if (!e->active) continue;
            if (hit_circle(cx_of(e->x, e->spr), cy_of(e->y, e->spr), e->r * 4 / 5,
                           px, py, PLAYER_HIT_R + 1)) {
                enemy_kill(e, false);
                kill_player();
                return;
            }
        }
        /* ボス本体 vs 自機 */
        if (boss.active && boss.state == BOSS_FIGHT &&
            hit_circle(cx_of(boss.x, boss.spr), cy_of(boss.y, boss.spr),
                       boss.r * 4 / 5, px, py, PLAYER_HIT_R + 1)) {
            kill_player();
            return;
        }
        /*
         * 中ボス vs 自機。
         * パーツは静止した時点から障害物になるので、触れると自機がやられる。
         * コアは攻撃が通る状態(=合体開始後)のみ当たる。飛来中は判定なし。
         */
        if (midBoss.active) {
            int k, tx, ty, tr, pr = spr_w(SPR_MIDPART) * 36 / 100;
            if (midBoss.partsSolid) {
                for (k = 0; k < 4; k++) {
                    midboss_part_pos(k, &tx, &ty);
                    if (hit_circle(tx, ty, pr * 4 / 5, px, py, PLAYER_HIT_R + 1)) {
                        kill_player();
                        return;
                    }
                }
            }
            if (midboss_core_vulnerable()) {
                midboss_core_target(&tx, &ty, &tr);
                if (hit_circle(tx, ty, tr * 4 / 5, px, py, PLAYER_HIT_R + 1)) {
                    kill_player();
                    return;
                }
            }
        }
    }

    /* アイテム回収(取りやすく判定を大きく) */
    for (i = 0; i < MAX_ITEMS; i++) {
        Item *it = &items[i];
        if (!it->active) continue;
        if (!hit_circle(FX2I(it->x) + spr_w(SPR_POWERUP) / 2,
                        FX2I(it->y) + spr_h(SPR_POWERUP) / 2, 9,
                        px, py, PLAYER_HIT_R + 11)) continue;
        it->active = false;
        snd_se(SE_POWERUP);
        if (gs.power < PLAYER_MAX_POWER) { gs.power++; gs.score += 500; }
        else                             { gs.score += 1000; }
        if (gs.score > gs.hiScore) gs.hiScore = gs.score;
    }
}

/* ============================================================ */
/* 編隊の出現                                                    */
/* ============================================================ */

static void run_spawners(void)
{
    int i;

    while (nextWave < stg->waveCount && stg->waves[nextWave].t <= stageT) {
        for (i = 0; i < MAX_SPAWNERS; i++) {
            if (!spawners[i].active) {
                spawners[i].active = true;
                spawners[i].wave = &stg->waves[nextWave];
                spawners[i].spawned = 0;
                spawners[i].timer = 0;
                break;
            }
        }
        nextWave++;
    }

    for (i = 0; i < MAX_SPAWNERS; i++) {
        Spawner *s = &spawners[i];
        const Wave *w;
        if (!s->active) continue;
        if (--s->timer > 0) continue;
        w = s->wave;
        {
            int bx = (w->x == X_RANDOM) ? (24 + game_rand(FIELD_W - 48)) : w->x;
            bool drop = (w->drop && s->spawned == w->n - 1);
            spawn_enemy(w, bx, drop);
        }
        s->spawned++;
        s->timer = w->interval;
        if (s->spawned >= w->n) s->active = false;
    }
}

/* ============================================================ */
/* ステージ開始 / 進行                                           */
/* ============================================================ */

static void reset_entities(void)
{
    memset(enemies, 0, sizeof(enemies));
    memset(ebullets, 0, sizeof(ebullets));
    memset(pbullets, 0, sizeof(pbullets));
    memset(items, 0, sizeof(items));
    memset(effects, 0, sizeof(effects));
    memset(spawners, 0, sizeof(spawners));
    memset(&boss, 0, sizeof(boss));
    memset(&midBoss, 0, sizeof(midBoss));
    enemyCount = 0;
    ebulletCount = 0;
    nextWave = 0;
}

static void start_stage(int idx)
{
    stageIdx = idx;
    gs.stageIdx = idx;
    stg = &stages[idx];

    reset_entities();
    player_reset();
    stageT = 0;
    midBossDone = false;
    midBossMsg = 0;
    deathTimer = 0;
    gameOverTimer = 0;
    scrollAccum = 0;
    paused = false;

    if (T_INVINC) gs.power = PLAYER_MAX_POWER;

    gfx_load_bg(stg->bg);
    gfx_bg_visible(true);
    txt_clear(SCREEN_TOP);
    txt_clear(SCREEN_BOTTOM);
    snd_bgm(stg->bgm);

    state = ST_INTRO;
    stateTimer = 150;
}

/* ---------- 中ボスの開始/終了 ---------- */
static void start_midboss_seq(void)
{
    state = ST_MIDBOSS;
    clear_center_msg();          /* ステージ名などが出ていたら消す */
    snd_bgm(BGM_MIDBOSS);        /* 不穏なBGMへ */
    midboss_start();
}

static void end_midboss_seq(void)
{
    midBoss.active = false;
    midBossDone = true;
    state = ST_PLAY;
    snd_bgm(stg->bgm);           /* ステージBGMへ戻す */
}

static void start_warning(void)
{
    int i;
    state = ST_WARNING;
    stateTimer = 160;
    for (i = 0; i < MAX_SPAWNERS; i++) spawners[i].active = false;
    nextWave = stg->waveCount;
    snd_bgm_stop();
    snd_se(SE_START);
}

static void start_boss(void)
{
    state = ST_BOSS;
    boss_start();
    snd_bgm(BGM_BOSS);
}

/* ============================================================ */
/* タイトル / ゲームオーバー / エンディング                      */
/* ============================================================ */

static void start_title(void)
{
    state = ST_TITLE;
    reset_entities();
    stateTimer = 0;
    titleArmed = false;
    paused = false;
    scrollAccum = 0;
    player.alive = false;
    gfx_load_bg(0);
    gfx_bg_visible(true);
    txt_clear(SCREEN_TOP);
    txt_clear(SCREEN_BOTTOM);
    snd_bgm(BGM_TITLE);
}

static void start_gameover(void)
{
    state = ST_GAMEOVER;
    stateTimer = 45;
    snd_bgm_stop();
    gfx_bg_visible(false);
    txt_clear(SCREEN_TOP);
    txt_clear(SCREEN_BOTTOM);
}

static const char *CREDITS[] = {
    "CONGRATULATIONS!",
    "",
    "PEACE RETURNS TO THE GALAXY.",
    "ALL OF THE MASTERS ARE",
    "WAITING FOR YOUR RETURN.",
    "",
    "-- STAFF --",
    "",
    "PROGRAM",
    "CLAUDE OPUS",
    "",
    "GRAPHICS",
    "PIXEL WORKS UNIT",
    "",
    "SOUND",
    "CHIPTUNE UNIT",
    "",
    "SPECIAL THANKS",
    "DEVKITPRO / LIBNDS",
    "MAXMOD",
    "MASTERS TEAM",
    "",
    "",
    "THANK YOU FOR PLAYING!",
};
#define CREDIT_LINES ((int)(sizeof(CREDITS) / sizeof(CREDITS[0])))
#define CREDIT_TOP_ROW 24

static void start_ending(void)
{
    int i;
    state = ST_ENDING;
    reset_entities();
    stateTimer = 60;
    creditScroll = 0;
    creditsDone = false;
    endShipY = I2FX(FIELD_H - 80);

    gfx_load_bg(0);
    gfx_bg_visible(true);
    txt_clear(SCREEN_TOP);
    txt_clear(SCREEN_BOTTOM);
    snd_bgm(BGM_ENDING);

    /* 上画面のテキスト層に流し込む(見えている24行の下に配置してスクロール) */
    for (i = 0; i < CREDIT_LINES; i++)
        txt_center(SCREEN_TOP, CREDIT_TOP_ROW + i, CREDITS[i],
                   (i == 0) ? TXT_GOLD : TXT_WHITE);
}

/* ============================================================ */
/* 描画                                                          */
/* ============================================================ */

static void draw_hud(void)
{
    txt_put(SCREEN_TOP, 0, 0, "SC", TXT_WHITE);
    txt_num(SCREEN_TOP, 3, 0, gs.score, 8, TXT_WHITE);
    txt_put(SCREEN_TOP, 0, 1, "HI", TXT_GREEN);
    txt_num(SCREEN_TOP, 3, 1, gs.hiScore, 8, TXT_GREEN);

    txt_put(SCREEN_TOP, 20, 0, "LIVES", TXT_RED);
    txt_num(SCREEN_TOP, 26, 0, (u32)(gs.lives < 0 ? 0 : gs.lives), 1, TXT_RED);
#ifdef TEST_MB_COUNT
    txt_put(SCREEN_TOP, 0, 3, "MERGE HITS", TXT_CYAN);
    txt_num(SCREEN_TOP, 11, 3, (u32)mbHitCount, 3, TXT_CYAN);
    txt_put(SCREEN_TOP, 16, 3, midBoss.active ? "ACTIVE" : "      ", TXT_GREY);
#endif
    txt_put(SCREEN_TOP, 20, 1, "PW", TXT_GOLD);
    txt_num(SCREEN_TOP, 23, 1, (u32)gs.power, 1, TXT_GOLD);
    txt_put(SCREEN_TOP, 24, 1, "/", TXT_GOLD);
    txt_num(SCREEN_TOP, 25, 1, PLAYER_MAX_POWER, 1, TXT_GOLD);
}

static void draw_boss_bar(void)
{
    char bar[31];
    int n, i;
    if (!boss.active || boss.maxHp <= 0) {
        txt_put(SCREEN_TOP, 1, 2, "                              ", TXT_RED);
        return;
    }
    n = boss.hp * 30 / boss.maxHp;
    for (i = 0; i < 30; i++) bar[i] = (i < n) ? '=' : ' ';
    bar[30] = 0;
    txt_put(SCREEN_TOP, 1, 2, bar, TXT_RED);
}

static void draw_center_msg(void)
{
    switch (state) {
    case ST_INTRO:
        txt_center(SCREEN_TOP, 11, stg->name, TXT_WHITE);
        txt_center(SCREEN_TOP, 13, stg->subtitle, TXT_CYAN);
        break;
    case ST_WARNING:
        if ((stateTimer % 20) < 12) {
            txt_center(SCREEN_TOP, 11, "WARNING!!", TXT_RED);
            txt_center(SCREEN_TOP, 13, stg->bossName, TXT_ORANGE);
        } else {
            txt_center(SCREEN_TOP, 11, "         ", TXT_RED);
            txt_center(SCREEN_TOP, 13, "                ", TXT_RED);
        }
        break;
    case ST_MIDBOSS:
        if (midBossMsg > 0) {
            txt_center(SCREEN_TOP, 11, "PERFECT!", TXT_GOLD);
            txt_center(SCREEN_TOP, 13, "BONUS", TXT_WHITE);
            txt_num(SCREEN_TOP, 19, 13, MB_BONUS_SCORE, 5, TXT_WHITE);
        }
        break;
    case ST_CLEAR:
        txt_center(SCREEN_TOP, 11, "STAGE CLEAR!", TXT_GOLD);
        txt_center(SCREEN_TOP, 13, "BONUS", TXT_WHITE);
        txt_num(SCREEN_TOP, 19, 13, stg->bossScore, 5, TXT_WHITE);
        break;
    default:
        break;
    }
}

static void clear_center_msg(void)
{
    txt_put(SCREEN_TOP, 0, 11, "                                ", TXT_WHITE);
    txt_put(SCREEN_TOP, 0, 13, "                                ", TXT_WHITE);
}

static void draw_entities(void)
{
    int i;

    spr_begin();

    /* 優先度の高い順に積む(OAMが尽きたとき落ちるのは後ろのもの) */
    if (player.alive && (player.invincible <= 0 || T_INVINC || (frameCounter & 4)))
        spr_draw(SPR_PLAYER, (frameCounter >> 2) & 1, FX2I(player.x), FX2I(player.y));

    if (boss.active) {
        bool show = true;
        if (boss.state == BOSS_DYING)      show = (boss.dyingAge & 2) != 0;
        else if (boss.flash > 0)           show = (frameCounter & 1) != 0;
        if (show)
            spr_draw(boss.spr, (frameCounter / 10) & 1, FX2I(boss.x), FX2I(boss.y));
    }

    /*
     * 中ボス。パーツを先に描き、コアを後に描く(=コアが手前)。
     * こうするとコアの装甲リングとソケットの爪がパーツの上に残り、
     * 「掴んで固定している」ように見える。
     * 静止中(無敵)は点滅させて、まだ攻撃が効かないことを示す。
     */
    if (midBoss.active) {
        bool show = true;
        int fr = (frameCounter / 8) & 1;
        if (midBoss.state == MB_DYING && midBoss.result != MBR_ESCAPED) {
            show = (midBoss.t & 2) != 0;
        } else if (midBoss.flash > 0) {
            show = (frameCounter & 1) != 0;
        } else if (midBoss.state == MB_HOLD) {
            show = (midBoss.t % 10) >= 5;
        }
        if (show) {
            int k, tx, ty, tr;
            if (midBoss.partsVisible) {
                for (k = 0; k < 4; k++) {
                    midboss_part_pos(k, &tx, &ty);
                    spr_draw(SPR_MIDPART, fr,
                             tx - spr_w(SPR_MIDPART) / 2,
                             ty - spr_h(SPR_MIDPART) / 2);
                }
            }
            midboss_core_target(&tx, &ty, &tr);
            spr_draw(SPR_MIDCORE, fr,
                     tx - spr_w(SPR_MIDCORE) / 2, ty - spr_h(SPR_MIDCORE) / 2);
        }
    }

    for (i = 0; i < MAX_ENEMIES; i++) {
        Enemy *e = &enemies[i];
        if (!e->active) continue;
        if (e->flash > 0 && !(frameCounter & 1)) continue;
        /* 地上物は優先度3で他のスプライトより奥に描く */
        spr_draw_prio(e->spr, (e->t >> 3) & 1, FX2I(e->x), FX2I(e->y),
                      (e->pattern == PAT_GROUND) ? 3 : 2);
    }

    for (i = 0; i < MAX_EBULLETS; i++)
        if (ebullets[i].active)
            spr_draw(SPR_BULLET_E, 0, FX2I(ebullets[i].x), FX2I(ebullets[i].y));

    for (i = 0; i < MAX_PBULLETS; i++)
        if (pbullets[i].active)
            spr_draw(SPR_BULLET_P, 0, FX2I(pbullets[i].x), FX2I(pbullets[i].y));

    for (i = 0; i < MAX_ITEMS; i++)
        if (items[i].active)
            spr_draw(SPR_POWERUP, (items[i].t / 6) & 1, FX2I(items[i].x), FX2I(items[i].y));

    for (i = 0; i < MAX_EFFECTS; i++) {
        Effect *fx = &effects[i];
        int f;
        if (!fx->active) continue;
        f = fx->t / 5;
        if (f > 3) f = 3;
        spr_draw(SPR_EXPLOSION, f, FX2I(fx->x), FX2I(fx->y));
    }

    spr_end();
}

/* ============================================================ */
/* 各シーンの1フレーム                                           */
/* ============================================================ */

static void frame_title(void)
{
    scrollAccum += FP(0.32);
    gfx_set_bg_scroll(scrollAccum);

    txt_center(SCREEN_TOP, 6, "STAR MASTERS", TXT_GOLD);
    txt_center(SCREEN_TOP, 8, "- 8BIT VERTICAL SHOOTER -", TXT_CYAN);
    if ((frameCounter % 60) < 38)
        txt_center(SCREEN_TOP, 14, "PRESS A TO START", TXT_WHITE);
    else
        txt_center(SCREEN_TOP, 14, "                ", TXT_WHITE);

    txt_center(SCREEN_BOTTOM, 4,  "MOVE   D-PAD / TOUCH", TXT_GREY);
    txt_center(SCREEN_BOTTOM, 6,  "SHOT   A B X Y", TXT_GREY);
    txt_center(SCREEN_BOTTOM, 8,  "PAUSE  START", TXT_GREY);
    txt_center(SCREEN_BOTTOM, 10, "MUTE   SELECT", TXT_GREY);
    txt_put(SCREEN_BOTTOM, 6, 14, "HI-SCORE", TXT_GREEN);
    txt_num(SCREEN_BOTTOM, 16, 14, gs.hiScore, 8, TXT_GREEN);
    txt_center(SCREEN_BOTTOM, 20, "(C) 2026 MASTERS TEAM", TXT_GREY);

    /* 自機を下画面に浮かべておく */
    spr_begin();
    spr_draw(SPR_PLAYER, (frameCounter >> 2) & 1,
             FIELD_W / 2 - spr_w(SPR_PLAYER) / 2,
             SCR_H + 128 + FX2I(SINFX(FP(6.0), frameCounter * 200)));
    spr_end();

    if (stateTimer > 0) {                    /* 開始演出 */
        if ((stateTimer % 6) < 3) txt_center(SCREEN_TOP, 14, "PRESS A TO START", TXT_WHITE);
        else                      txt_center(SCREEN_TOP, 14, "                ", TXT_WHITE);
        if (--stateTimer == 0) {
            gs.score = 0;
            gs.lives = PLAYER_LIVES;
            gs.power = 1;
            start_stage(0);
        }
        return;
    }

    if (T_AUTOSTART && frameCounter > 120) {     /* 動作確認ビルドは自動で開始 */
        stateTimer = 45;
        game_srand(0xC0FFEEu);
        snd_se(SE_START);
        snd_bgm_stop();
        return;
    }

    if (!keysShot()) titleArmed = true;
    else if (titleArmed) {
        stateTimer = 45;
        game_srand((u32)frameCounter * 2654435761u + 12345u);
        snd_se(SE_START);
        snd_bgm_stop();
    }
}

static void frame_gameover(void)
{
    txt_center(SCREEN_TOP, 8, "GAME OVER", TXT_RED);
    txt_put(SCREEN_TOP, 8, 13, "SCORE", TXT_WHITE);
    txt_num(SCREEN_TOP, 16, 13, gs.score, 8, TXT_WHITE);
    txt_put(SCREEN_TOP, 8, 15, "HI", TXT_GREEN);
    txt_num(SCREEN_TOP, 16, 15, gs.hiScore, 8, TXT_GREEN);

    if ((frameCounter % 60) < 38)
        txt_center(SCREEN_BOTTOM, 10, "PRESS A FOR TITLE", TXT_WHITE);
    else
        txt_center(SCREEN_BOTTOM, 10, "                 ", TXT_WHITE);

    spr_begin();
    spr_end();

    if (stateTimer > 0) { stateTimer--; return; }
    if (keysDown() & (KEY_A | KEY_B | KEY_X | KEY_Y | KEY_START)) start_title();
}

static void frame_ending(void)
{
    scrollAccum += FP(0.24);
    gfx_set_bg_scroll(scrollAccum);

    if (!creditsDone) {
        creditScroll += FP(0.44);
        txt_scroll(SCREEN_TOP, FX2I(creditScroll));
        if (FX2I(creditScroll) >= (CREDIT_TOP_ROW + CREDIT_LINES) * 8) {
            creditsDone = true;
            txt_clear(SCREEN_TOP);
            stateTimer = 60;
        }
    } else {
        txt_center(SCREEN_TOP, 9, "THE END", TXT_GOLD);
        txt_put(SCREEN_TOP, 5, 13, "FINAL SCORE", TXT_WHITE);
        txt_num(SCREEN_TOP, 18, 13, gs.score, 8, TXT_WHITE);
        if ((frameCounter % 60) < 38)
            txt_center(SCREEN_BOTTOM, 20, "PRESS A FOR TITLE", TXT_GREY);
        else
            txt_center(SCREEN_BOTTOM, 20, "                 ", TXT_GREY);
        if (stateTimer > 0) stateTimer--;
        else if (keysDown() & (KEY_A | KEY_B | KEY_X | KEY_Y | KEY_START)) {
            snd_bgm_stop();
            start_title();
            return;
        }
    }

    /* 自機が下画面をゆっくり上っていく */
    if (endShipY > I2FX(SCR_H + 16)) endShipY -= FP(0.32);
    spr_begin();
    spr_draw(SPR_PLAYER, (frameCounter >> 2) & 1,
             FIELD_W / 2 - spr_w(SPR_PLAYER) / 2, FX2I(endShipY));
    spr_end();
}

static void frame_stage(void)
{
    scrollAccum += stg->scroll;
    gfx_set_bg_scroll(scrollAccum);

    switch (state) {
    case ST_INTRO:
        if (--stateTimer <= 0) { state = ST_PLAY; clear_center_msg(); }
        break;
    case ST_PLAY:
        stageT++;
        run_spawners();
        if (!midBossDone && MIDBOSS_AT(stg) && stageT >= MIDBOSS_AT(stg)) {
            start_midboss_seq();
        } else if (stageT >= BOSS_AT(stg) && enemyCount == 0) {
            start_warning();
        }
        break;
    case ST_MIDBOSS:
        /* 中ボス中は新しい編隊を出さない(stageT も進めない)。
           既に出ている敵と地上物はそのまま流れていく */
        break;
    case ST_WARNING:
        if (--stateTimer <= 0) { clear_center_msg(); start_boss(); }
        break;
    case ST_CLEAR:
        if (--stateTimer <= 0) {
            clear_center_msg();
            if (stageIdx + 1 < STAGE_COUNT) start_stage(stageIdx + 1);
            else                            start_ending();
            return;
        }
        break;
    default:
        break;
    }

    if (deathTimer > 0 && --deathTimer == 0) respawn();
    if (gameOverTimer > 0 && --gameOverTimer == 0) { start_gameover(); return; }

    player_update();
    {
        int i;
        for (i = 0; i < MAX_ENEMIES; i++)
            if (enemies[i].active) enemy_update(&enemies[i]);
    }
    bullets_update();
    items_update();
    effects_update();
    if (boss.active) boss_update();
    if (midBoss.active) {
        if (!midboss_update()) end_midboss_seq();
    }

    /* ボーナス表示は状態に関わらず消す */
    if (midBossMsg > 0 && --midBossMsg == 0) clear_center_msg();

    collide();

    draw_hud();
    draw_boss_bar();
    draw_center_msg();
    draw_entities();
}

/* ============================================================ */
/* 公開API                                                       */
/* ============================================================ */

void game_init(void)
{
    memset(&gs, 0, sizeof(gs));
    gs.lives = PLAYER_LIVES;
    gs.power = 1;
    frameCounter = 0;
    start_title();
}

void game_frame(void)
{
    scanKeys();
    frameCounter++;

    /* SELECT: ミュート */
    if (keysDown() & KEY_SELECT) snd_toggle_mute();

    /* START: ポーズ(ステージ中のみ) */
    if ((keysDown() & KEY_START) &&
        (state == ST_INTRO || state == ST_PLAY ||
         state == ST_WARNING || state == ST_BOSS || state == ST_CLEAR)) {
        paused = !paused;
        if (paused) txt_center(SCREEN_TOP, 17, "PAUSE", TXT_GOLD);
        else        txt_put(SCREEN_TOP, 0, 17, "                                ", TXT_WHITE);
    }
    if (paused) return;

    switch (state) {
    case ST_TITLE:    frame_title();    break;
    case ST_GAMEOVER: frame_gameover(); break;
    case ST_ENDING:   frame_ending();   break;
    default:          frame_stage();    break;
    }
}
