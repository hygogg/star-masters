/*
 * stages.c — 全3ステージの敵出現テーブル
 *
 * Web版 js/config.js からの移植。x座標と速度は x0.8。
 * 対応表: 40->32  50->40  70->56  80->64  90->72  100->80  110->88  120->96
 *         130->104 160->128 200->160 210->168 220->176 230->184 250->200
 *         270->216 280->224
 */
#include "stages.h"
#include "sound.h"

/* ---------------- STAGE 1 ---------------- */
static const Wave waves1[] = {
    /* t,    spr,          pattern,      n, intv,  x,        hp, speed,      score, shoot, drop */
    {  150, SPR_ENEMY1,   PAT_SINE,     5, 22,  56,        1, FP(1.44),  100,   0,   false },
    {  340, SPR_ENEMY1,   PAT_SINE,     5, 22, 200,        1, FP(1.44),  100,   0,   false },
    {  420, SPR_GTURRET, PAT_GROUND,   2, 45, 48,        2, 0,          200, 100,   false },
    {  560, SPR_ENEMY2,   PAT_STRAIGHT, 6, 26, X_RANDOM,   1, FP(1.76),  150, 130,   false },
    {  700, SPR_GRADAR,  PAT_GROUND,   1,  0, 200,       1, 0,          400,   0,   false },
    {  800, SPR_ENEMY1,   PAT_SWOOP_L,  4, 20,  32,        1, FP(1.92),  100,   0,   false },
    {  990, SPR_ENEMY1,   PAT_SWOOP_R,  4, 20, 224,        1, FP(1.92),  100,   0,   false },
    { 1050, SPR_GTURRET, PAT_GROUND,   3, 35, X_RANDOM,  2, 0,          200, 110,   false },
    { 1200, SPR_MIDENEMY, PAT_HOVER,    1,  0, 128,       10, FP(1.12),  500,  70,   true  },
    { 1450, SPR_ENEMY2,   PAT_SINE,     6, 24, 128,        1, FP(1.60),  150, 150,   false },
    { 1700, SPR_ENEMY1,   PAT_STRAIGHT, 8, 16, X_RANDOM,   1, FP(2.08),  100,   0,   false },
    { 1950, SPR_ENEMY2,   PAT_SWOOP_R,  4, 22, 216,        2, FP(1.76),  150, 120,   false },
    { 2200, SPR_MIDENEMY, PAT_HOVER,    2, 90,  72,       10, FP(1.12),  500,  65,   true  },
    { 2350, SPR_GRADAR,  PAT_GROUND,   2, 60, 56,        1, 0,          400,   0,   false },
    { 2500, SPR_ENEMY1,   PAT_SINE,     6, 18,  96,        1, FP(1.92),  100,   0,   false },
    { 2600, SPR_GTURRET, PAT_GROUND,   2, 40, 184,       2, 0,          200,  95,   false },
    { 2700, SPR_ENEMY2,   PAT_STRAIGHT, 6, 20, X_RANDOM,   1, FP(2.08),  150, 110,   false },
};

/* ---------------- STAGE 2 ---------------- */
static const Wave waves2[] = {
    {  150, SPR_ENEMY2,   PAT_SINE,     6, 20,  72,        1, FP(1.76),  150, 140,   false },
    {  380, SPR_ENEMY3,   PAT_STRAIGHT, 5, 24, X_RANDOM,   2, FP(1.92),  200, 110,   false },
    {  500, SPR_GTURRET, PAT_GROUND,   2, 45, 64,        2, 0,          200,  95,   false },
    {  620, SPR_ENEMY1,   PAT_SWOOP_L,  5, 18,  32,        1, FP(2.24),  100,   0,   false },
    {  800, SPR_ENEMY1,   PAT_SWOOP_R,  5, 18, 224,        1, FP(2.24),  100,   0,   false },
    {  900, SPR_GRADAR,  PAT_GROUND,   1,  0, 160,       1, 0,          400,   0,   false },
    { 1000, SPR_MIDENEMY, PAT_HOVER,    2, 80,  88,       12, FP(1.20),  500,  60,   true  },
    { 1280, SPR_ENEMY3,   PAT_SINE,     6, 22, 160,        2, FP(1.92),  200, 100,   false },
    { 1400, SPR_GTURRET, PAT_GROUND,   3, 32, X_RANDOM,  2, 0,          200, 100,   false },
    { 1520, SPR_ENEMY2,   PAT_STRAIGHT, 8, 15, X_RANDOM,   1, FP(2.24),  150, 130,   false },
    { 1760, SPR_ENEMY3,   PAT_SWOOP_L,  4, 20,  40,        2, FP(2.08),  200,  90,   false },
    { 1980, SPR_ENEMY3,   PAT_SWOOP_R,  4, 20, 216,        2, FP(2.08),  200,  90,   false },
    { 2220, SPR_MIDENEMY, PAT_HOVER,    2, 70, 168,       12, FP(1.20),  500,  55,   true  },
    { 2400, SPR_GRADAR,  PAT_GROUND,   2, 55, 88,        1, 0,          400,   0,   false },
    { 2500, SPR_ENEMY2,   PAT_SINE,     8, 14, 128,        1, FP(2.40),  150, 120,   false },
    { 2650, SPR_GTURRET, PAT_GROUND,   2, 38, 152,       2, 0,          200,  90,   false },
    { 2760, SPR_ENEMY3,   PAT_STRAIGHT, 7, 18, X_RANDOM,   2, FP(2.24),  200,  90,   false },
};

/* ---------------- STAGE 3 ---------------- */
static const Wave waves3[] = {
    {  150, SPR_ENEMY3,   PAT_SINE,     6, 18,  80,        2, FP(2.08),  200, 100,   false },
    {  380, SPR_ENEMY1,   PAT_SWOOP_L,  6, 14,  32,        1, FP(2.56),  100,   0,   false },
    {  460, SPR_GTURRET, PAT_GROUND,   3, 38, 48,        2, 0,          200,  90,   false },
    {  540, SPR_ENEMY1,   PAT_SWOOP_R,  6, 14, 224,        1, FP(2.56),  100,   0,   false },
    {  760, SPR_ENEMY2,   PAT_STRAIGHT, 8, 14, X_RANDOM,   1, FP(2.40),  150, 110,   false },
    {  880, SPR_GRADAR,  PAT_GROUND,   2, 50, 184,       1, 0,          400,   0,   false },
    { 1000, SPR_MIDENEMY, PAT_HOVER,    3, 70,  64,       14, FP(1.28),  500,  50,   true  },
    { 1320, SPR_ENEMY3,   PAT_SINE,     8, 16, 176,        2, FP(2.24),  200,  85,   false },
    { 1400, SPR_GTURRET, PAT_GROUND,   3, 30, X_RANDOM,  2, 0,          200,  85,   false },
    { 1580, SPR_ENEMY2,   PAT_SWOOP_L,  5, 16,  40,        1, FP(2.56),  150, 100,   false },
    { 1780, SPR_ENEMY2,   PAT_SWOOP_R,  5, 16, 216,        1, FP(2.56),  150, 100,   false },
    { 2000, SPR_ENEMY3,   PAT_STRAIGHT, 9, 13, X_RANDOM,   2, FP(2.40),  200,  80,   false },
    { 2150, SPR_GTURRET, PAT_GROUND,   4, 34, X_RANDOM,  2, 0,          200,  80,   false },
    { 2260, SPR_MIDENEMY, PAT_HOVER,    2, 60, 184,       14, FP(1.28),  500,  45,   true  },
    { 2540, SPR_ENEMY1,   PAT_SINE,    10, 11, 128,        1, FP(2.72),  100,   0,   false },
    { 2700, SPR_GRADAR,  PAT_GROUND,   2, 48, 104,       1, 0,          400,   0,   false },
    { 2780, SPR_ENEMY3,   PAT_SINE,     8, 15, 104,        2, FP(2.40),  200,  75,   false },
};

const Stage stages[STAGE_COUNT] = {
    {
        "STAGE 1", "DEPARTURE",
        0, BGM_STAGE1, FP(0.80),
        waves1, sizeof(waves1) / sizeof(waves1[0]),
        1620, 3050, 1, SPR_BOSS1, "GUARDIAN", 300, 5000
    },
    {
        "STAGE 2", "CRIMSON NEBULA",
        1, BGM_STAGE2, FP(1.12),
        waves2, sizeof(waves2) / sizeof(waves2[0]),
        1680, 3100, 2, SPR_BOSS2, "CRIMSON TWIN", 500, 8000
    },
    {
        "STAGE 3", "OMEGA FORTRESS",
        2, BGM_STAGE3, FP(1.44),
        waves3, sizeof(waves3) / sizeof(waves3[0]),
        1480, 3150, 3, SPR_BOSS3, "OMEGA CORE", 800, 20000
    },
};
