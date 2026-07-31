/*
 * config.js — ゲーム全体の設定とステージ定義
 *
 * 難易度調整・ステージ構成の変更はこのファイルだけで完結する。
 * waves の各要素:
 *   t          出現フレーム(60fps 基準)
 *   type       ASSETS.img のキー (enemy1 / enemy2 / enemy3 / midenemy)
 *   pattern    移動パターン (straight / sine / swoopL / swoopR / hover)
 *   n          出現数 / interval 出現間隔(フレーム)
 *   x          出現x座標(スプライト中心)。'random' で毎回ランダム
 *   hp, speed, score
 *   shootEvery 何フレームごとに自機狙い弾を撃つか(0=撃たない)
 *   drop       true なら編隊の最後の1機がパワーアップを落とす
 */
var CONFIG = {
    TITLE: 'STAR MASTERS',
    WIDTH: 320,
    HEIGHT: 480,
    FPS: 60,

    PLAYER: {
        speed: 3.4,
        shotInterval: 6,   // 連射間隔(フレーム)
        hitR: 4,           // 自機の当たり判定半径(見た目より小さく)
        lives: 3,
        respawnInvincible: 150,
        maxPower: 3
    },

    BULLET: {
        playerSpeed: 10,
        enemySpeed: 2.6
    },

    HISCORE_KEY: 'star-masters-hiscore',

    CREDITS: [
        'CONGRATULATIONS!',
        '',
        '銀河に平和が戻った。',
        'すべてのマスターズが',
        'きみの帰りを待っている。',
        '',
        '-- STAFF --',
        '',
        'PROGRAM',
        '  CLAUDE FABLE',
        '',
        'GRAPHICS',
        '  PIXEL WORKS UNIT',
        '',
        'SOUND',
        '  CHIPTUNE UNIT',
        '',
        'SPECIAL THANKS',
        '  enchant.js',
        '  MASTERS TEAM',
        '',
        '',
        'THANK YOU FOR PLAYING!'
    ],

    STAGES: [
        /* ---------------- STAGE 1 ---------------- */
        {
            name: 'STAGE 1',
            subtitle: 'DEPARTURE',
            bg: 'bg1',
            bgm: 'stage1',
            scroll: 1.0,
            waves: [
                { t: 150,  type: 'enemy1', pattern: 'sine',    n: 5, interval: 22, x: 70,       hp: 1, speed: 1.8, score: 100, shootEvery: 0 },
                { t: 340,  type: 'enemy1', pattern: 'sine',    n: 5, interval: 22, x: 250,      hp: 1, speed: 1.8, score: 100, shootEvery: 0 },
                { t: 560,  type: 'enemy2', pattern: 'straight',n: 6, interval: 26, x: 'random', hp: 1, speed: 2.2, score: 150, shootEvery: 130 },
                { t: 800,  type: 'enemy1', pattern: 'swoopL',  n: 4, interval: 20, x: 40,       hp: 1, speed: 2.4, score: 100, shootEvery: 0 },
                { t: 990,  type: 'enemy1', pattern: 'swoopR',  n: 4, interval: 20, x: 280,      hp: 1, speed: 2.4, score: 100, shootEvery: 0 },
                { t: 1200, type: 'midenemy', pattern: 'hover', n: 1, interval: 0,  x: 160,      hp: 10, speed: 1.4, score: 500, shootEvery: 70, drop: true },
                { t: 1450, type: 'enemy2', pattern: 'sine',    n: 6, interval: 24, x: 160,      hp: 1, speed: 2.0, score: 150, shootEvery: 150 },
                { t: 1700, type: 'enemy1', pattern: 'straight',n: 8, interval: 16, x: 'random', hp: 1, speed: 2.6, score: 100, shootEvery: 0 },
                { t: 1950, type: 'enemy2', pattern: 'swoopR',  n: 4, interval: 22, x: 270,      hp: 2, speed: 2.2, score: 150, shootEvery: 120 },
                { t: 2200, type: 'midenemy', pattern: 'hover', n: 2, interval: 90, x: 90,       hp: 10, speed: 1.4, score: 500, shootEvery: 65, drop: true },
                { t: 2500, type: 'enemy1', pattern: 'sine',    n: 6, interval: 18, x: 120,      hp: 1, speed: 2.4, score: 100, shootEvery: 0 },
                { t: 2700, type: 'enemy2', pattern: 'straight',n: 6, interval: 20, x: 'random', hp: 1, speed: 2.6, score: 150, shootEvery: 110 }
            ],
            bossAt: 3050,   // このフレームで WARNING → ボス戦
            boss: {
                id: 1, img: 'boss1', name: 'GUARDIAN',
                hp: 300, score: 5000
            }
        },

        /* ---------------- STAGE 2 ---------------- */
        {
            name: 'STAGE 2',
            subtitle: 'CRIMSON NEBULA',
            bg: 'bg2',
            bgm: 'stage2',
            scroll: 1.4,
            waves: [
                { t: 150,  type: 'enemy2', pattern: 'sine',    n: 6, interval: 20, x: 90,       hp: 1, speed: 2.2, score: 150, shootEvery: 140 },
                { t: 380,  type: 'enemy3', pattern: 'straight',n: 5, interval: 24, x: 'random', hp: 2, speed: 2.4, score: 200, shootEvery: 110 },
                { t: 620,  type: 'enemy1', pattern: 'swoopL',  n: 5, interval: 18, x: 40,       hp: 1, speed: 2.8, score: 100, shootEvery: 0 },
                { t: 800,  type: 'enemy1', pattern: 'swoopR',  n: 5, interval: 18, x: 280,      hp: 1, speed: 2.8, score: 100, shootEvery: 0 },
                { t: 1000, type: 'midenemy', pattern: 'hover', n: 2, interval: 80, x: 110,      hp: 12, speed: 1.5, score: 500, shootEvery: 60, drop: true },
                { t: 1280, type: 'enemy3', pattern: 'sine',    n: 6, interval: 22, x: 200,      hp: 2, speed: 2.4, score: 200, shootEvery: 100 },
                { t: 1520, type: 'enemy2', pattern: 'straight',n: 8, interval: 15, x: 'random', hp: 1, speed: 2.8, score: 150, shootEvery: 130 },
                { t: 1760, type: 'enemy3', pattern: 'swoopL',  n: 4, interval: 20, x: 50,       hp: 2, speed: 2.6, score: 200, shootEvery: 90 },
                { t: 1980, type: 'enemy3', pattern: 'swoopR',  n: 4, interval: 20, x: 270,      hp: 2, speed: 2.6, score: 200, shootEvery: 90 },
                { t: 2220, type: 'midenemy', pattern: 'hover', n: 2, interval: 70, x: 210,      hp: 12, speed: 1.5, score: 500, shootEvery: 55, drop: true },
                { t: 2500, type: 'enemy2', pattern: 'sine',    n: 8, interval: 14, x: 160,      hp: 1, speed: 3.0, score: 150, shootEvery: 120 },
                { t: 2760, type: 'enemy3', pattern: 'straight',n: 7, interval: 18, x: 'random', hp: 2, speed: 2.8, score: 200, shootEvery: 90 }
            ],
            bossAt: 3100,
            boss: {
                id: 2, img: 'boss2', name: 'CRIMSON TWIN',
                hp: 500, score: 8000
            }
        },

        /* ---------------- STAGE 3 ---------------- */
        {
            name: 'STAGE 3',
            subtitle: 'OMEGA FORTRESS',
            bg: 'bg3',
            bgm: 'stage3',
            scroll: 1.8,
            waves: [
                { t: 150,  type: 'enemy3', pattern: 'sine',    n: 6, interval: 18, x: 100,      hp: 2, speed: 2.6, score: 200, shootEvery: 100 },
                { t: 380,  type: 'enemy1', pattern: 'swoopL',  n: 6, interval: 14, x: 40,       hp: 1, speed: 3.2, score: 100, shootEvery: 0 },
                { t: 540,  type: 'enemy1', pattern: 'swoopR',  n: 6, interval: 14, x: 280,      hp: 1, speed: 3.2, score: 100, shootEvery: 0 },
                { t: 760,  type: 'enemy2', pattern: 'straight',n: 8, interval: 14, x: 'random', hp: 1, speed: 3.0, score: 150, shootEvery: 110 },
                { t: 1000, type: 'midenemy', pattern: 'hover', n: 3, interval: 70, x: 80,       hp: 14, speed: 1.6, score: 500, shootEvery: 50, drop: true },
                { t: 1320, type: 'enemy3', pattern: 'sine',    n: 8, interval: 16, x: 220,      hp: 2, speed: 2.8, score: 200, shootEvery: 85 },
                { t: 1580, type: 'enemy2', pattern: 'swoopL',  n: 5, interval: 16, x: 50,       hp: 1, speed: 3.2, score: 150, shootEvery: 100 },
                { t: 1780, type: 'enemy2', pattern: 'swoopR',  n: 5, interval: 16, x: 270,      hp: 1, speed: 3.2, score: 150, shootEvery: 100 },
                { t: 2000, type: 'enemy3', pattern: 'straight',n: 9, interval: 13, x: 'random', hp: 2, speed: 3.0, score: 200, shootEvery: 80 },
                { t: 2260, type: 'midenemy', pattern: 'hover', n: 2, interval: 60, x: 230,      hp: 14, speed: 1.6, score: 500, shootEvery: 45, drop: true },
                { t: 2540, type: 'enemy1', pattern: 'sine',    n: 10, interval: 11, x: 160,     hp: 1, speed: 3.4, score: 100, shootEvery: 0 },
                { t: 2780, type: 'enemy3', pattern: 'sine',    n: 8, interval: 15, x: 130,      hp: 2, speed: 3.0, score: 200, shootEvery: 75 }
            ],
            bossAt: 3150,
            boss: {
                id: 3, img: 'boss3', name: 'OMEGA CORE',
                hp: 800, score: 20000
            }
        }
    ]
};
