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
    POWERED_BY: 'POWERED BY CYO',
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

    /*
     * ---------- 中ボス ----------
     * 各ステージの中間で出現する。演出の流れ:
     *   1. 不穏なBGMに切り替わり、コアが画面上部から降りてきて止まる
     *   2. 4つのパーツが画面の四方(外)から飛び込んでくる (flyInFrames)
     *      → 飛来中は当たり判定なし
     *   3. コアの四方で holdFrames だけ静止
     *      → ここからパーツは常に無敵の障害物になる
     *        (ショットを弾き、自機が触れると死ぬ)
     *      → コアへの攻撃はまだ効かない
     *   4. パーツが移動を始め、mergeFrames かけてコアと合体
     *      → この猶予の間にコアへ hpMerge 発当てると bonusScore + ファンファーレ
     *   5. 合体してしまうと通常形態。コアへ hpFull 発当てると normalScore
     *
     * パーツは最後まで無敵なので、狙えるのはコアだけ。
     */
    MIDBOSS: {
        /*
         * 必要被弾数。パーツは常に無敵でショットを弾くため、狙えるのはコアだけ。
         * さらに下側のパーツがコアの中央を遮るので、コアの左右の縁を狙う必要がある。
         * hpMerge は「最大パワーでギリギリ倒せる」値に実測で合わせてある
         * (tools/measure_midboss.js 参照)。
         */
        /*
         * 実測値(tools/measure_midboss.js, パワー3・最適位置に固定して撃ちっぱなし):
         *   後方から安全に撃つ (y>=230) …………………… 11〜12発が上限
         *   閉じてくるパーツの間に踏み込む (y=200,dx=±16) … 22発
         *   その手前 (y=200,dx=±24 / y=215,dx=±16) ……… 13〜16発
         *   ※ y=200,dx=0/±8 は下パーツの進路上なので死ぬ
         * → 14 にすると「後方から撃つだけでは届かず、踏み込んだときだけ取れる」。
         *   パワー1(上限9発)では不可能で、パワーアップが前提になる。
         */
        hpMerge: 14,         // 合体前(ボーナス猶予中)に必要な被弾数
        hpFull: 8,           // 合体後に必要な被弾数(時間制限がないので据え置き)
        flyInFrames: 45,     // パーツが画面外から静止位置まで来るのにかかる時間
        holdFrames: 60,      // 静止(1秒)。ここからパーツに当たり判定が生まれる
        mergeFrames: 60,     // 移動開始から合体まで(1秒)。ボーナスの猶予
        coreY: 118,          // コアが止まるy(左上)
        ringR: 80,           // 静止中のパーツのコア中心からの距離
        attachR: 24,         // 合体後のパーツのコア中心からの距離
        bonusScore: 50000,   // 合体前に破壊
        normalScore: 1000,   // 合体後に破壊
        fullTimeout: 1200,   // 合体後これだけ倒せないと去る(進行不能の防止)
        shootEvery: 50       // 合体後の攻撃間隔
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
                { t: 420,  type: 'gturret', pattern: 'ground',n: 2, interval: 45, x: 60,       hp: 2, speed: 0,   score: 200, shootEvery: 100 },
                { t: 560,  type: 'enemy2', pattern: 'straight',n: 6, interval: 26, x: 'random', hp: 1, speed: 2.2, score: 150, shootEvery: 130 },
                { t: 700,  type: 'gradar', pattern: 'ground', n: 1, interval: 0,  x: 250,      hp: 1, speed: 0,   score: 400, shootEvery: 0 },
                { t: 800,  type: 'enemy1', pattern: 'swoopL',  n: 4, interval: 20, x: 40,       hp: 1, speed: 2.4, score: 100, shootEvery: 0 },
                { t: 990,  type: 'enemy1', pattern: 'swoopR',  n: 4, interval: 20, x: 280,      hp: 1, speed: 2.4, score: 100, shootEvery: 0 },
                { t: 1050, type: 'gturret', pattern: 'ground',n: 3, interval: 35, x: 'random', hp: 2, speed: 0,   score: 200, shootEvery: 110 },
                { t: 1200, type: 'midenemy', pattern: 'hover', n: 1, interval: 0,  x: 160,      hp: 10, speed: 1.4, score: 500, shootEvery: 70, drop: true },
                { t: 1450, type: 'enemy2', pattern: 'sine',    n: 6, interval: 24, x: 160,      hp: 1, speed: 2.0, score: 150, shootEvery: 150 },
                { t: 1700, type: 'enemy1', pattern: 'straight',n: 8, interval: 16, x: 'random', hp: 1, speed: 2.6, score: 100, shootEvery: 0 },
                { t: 1950, type: 'enemy2', pattern: 'swoopR',  n: 4, interval: 22, x: 270,      hp: 2, speed: 2.2, score: 150, shootEvery: 120 },
                { t: 2200, type: 'midenemy', pattern: 'hover', n: 2, interval: 90, x: 90,       hp: 10, speed: 1.4, score: 500, shootEvery: 65, drop: true },
                { t: 2350, type: 'gradar', pattern: 'ground', n: 2, interval: 60, x: 70,       hp: 1, speed: 0,   score: 400, shootEvery: 0 },
                { t: 2500, type: 'enemy1', pattern: 'sine',    n: 6, interval: 18, x: 120,      hp: 1, speed: 2.4, score: 100, shootEvery: 0 },
                { t: 2600, type: 'gturret', pattern: 'ground',n: 2, interval: 40, x: 230,      hp: 2, speed: 0,   score: 200, shootEvery: 95 },
                { t: 2700, type: 'enemy2', pattern: 'straight',n: 6, interval: 20, x: 'random', hp: 1, speed: 2.6, score: 150, shootEvery: 110 }
            ],
            midBossAt: 1620,  // このフレームで中ボス演出へ
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
                { t: 500,  type: 'gturret', pattern: 'ground', n: 2, interval: 45, x: 80,         hp: 2, speed: 0,   score: 200, shootEvery: 95 },
                { t: 620,  type: 'enemy1', pattern: 'swoopL',  n: 5, interval: 18, x: 40,       hp: 1, speed: 2.8, score: 100, shootEvery: 0 },
                { t: 800,  type: 'enemy1', pattern: 'swoopR',  n: 5, interval: 18, x: 280,      hp: 1, speed: 2.8, score: 100, shootEvery: 0 },
                { t: 900,  type: 'gradar', pattern: 'ground',  n: 1, interval:  0, x: 200,        hp: 1, speed: 0,   score: 400, shootEvery: 0 },
                { t: 1000, type: 'midenemy', pattern: 'hover', n: 2, interval: 80, x: 110,      hp: 12, speed: 1.5, score: 500, shootEvery: 60, drop: true },
                { t: 1280, type: 'enemy3', pattern: 'sine',    n: 6, interval: 22, x: 200,      hp: 2, speed: 2.4, score: 200, shootEvery: 100 },
                { t: 1400, type: 'gturret', pattern: 'ground', n: 3, interval: 32, x: 'random',   hp: 2, speed: 0,   score: 200, shootEvery: 100 },
                { t: 1520, type: 'enemy2', pattern: 'straight',n: 8, interval: 15, x: 'random', hp: 1, speed: 2.8, score: 150, shootEvery: 130 },
                { t: 1760, type: 'enemy3', pattern: 'swoopL',  n: 4, interval: 20, x: 50,       hp: 2, speed: 2.6, score: 200, shootEvery: 90 },
                { t: 1980, type: 'enemy3', pattern: 'swoopR',  n: 4, interval: 20, x: 270,      hp: 2, speed: 2.6, score: 200, shootEvery: 90 },
                { t: 2220, type: 'midenemy', pattern: 'hover', n: 2, interval: 70, x: 210,      hp: 12, speed: 1.5, score: 500, shootEvery: 55, drop: true },
                { t: 2400, type: 'gradar', pattern: 'ground',  n: 2, interval: 55, x: 110,        hp: 1, speed: 0,   score: 400, shootEvery: 0 },
                { t: 2500, type: 'enemy2', pattern: 'sine',    n: 8, interval: 14, x: 160,      hp: 1, speed: 3.0, score: 150, shootEvery: 120 },
                { t: 2650, type: 'gturret', pattern: 'ground', n: 2, interval: 38, x: 190,        hp: 2, speed: 0,   score: 200, shootEvery: 90 },
                { t: 2760, type: 'enemy3', pattern: 'straight',n: 7, interval: 18, x: 'random', hp: 2, speed: 2.8, score: 200, shootEvery: 90 }
            ],
            midBossAt: 1680,  // このフレームで中ボス演出へ
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
                { t: 460,  type: 'gturret', pattern: 'ground', n: 3, interval: 38, x: 60,         hp: 2, speed: 0,   score: 200, shootEvery: 90 },
                { t: 540,  type: 'enemy1', pattern: 'swoopR',  n: 6, interval: 14, x: 280,      hp: 1, speed: 3.2, score: 100, shootEvery: 0 },
                { t: 760,  type: 'enemy2', pattern: 'straight',n: 8, interval: 14, x: 'random', hp: 1, speed: 3.0, score: 150, shootEvery: 110 },
                { t: 880,  type: 'gradar', pattern: 'ground',  n: 2, interval: 50, x: 230,        hp: 1, speed: 0,   score: 400, shootEvery: 0 },
                { t: 1000, type: 'midenemy', pattern: 'hover', n: 3, interval: 70, x: 80,       hp: 14, speed: 1.6, score: 500, shootEvery: 50, drop: true },
                { t: 1320, type: 'enemy3', pattern: 'sine',    n: 8, interval: 16, x: 220,      hp: 2, speed: 2.8, score: 200, shootEvery: 85 },
                { t: 1400, type: 'gturret', pattern: 'ground', n: 3, interval: 30, x: 'random',   hp: 2, speed: 0,   score: 200, shootEvery: 85 },
                { t: 1580, type: 'enemy2', pattern: 'swoopL',  n: 5, interval: 16, x: 50,       hp: 1, speed: 3.2, score: 150, shootEvery: 100 },
                { t: 1780, type: 'enemy2', pattern: 'swoopR',  n: 5, interval: 16, x: 270,      hp: 1, speed: 3.2, score: 150, shootEvery: 100 },
                { t: 2000, type: 'enemy3', pattern: 'straight',n: 9, interval: 13, x: 'random', hp: 2, speed: 3.0, score: 200, shootEvery: 80 },
                { t: 2150, type: 'gturret', pattern: 'ground', n: 4, interval: 34, x: 'random',   hp: 2, speed: 0,   score: 200, shootEvery: 80 },
                { t: 2260, type: 'midenemy', pattern: 'hover', n: 2, interval: 60, x: 230,      hp: 14, speed: 1.6, score: 500, shootEvery: 45, drop: true },
                { t: 2540, type: 'enemy1', pattern: 'sine',    n: 10, interval: 11, x: 160,     hp: 1, speed: 3.4, score: 100, shootEvery: 0 },
                { t: 2700, type: 'gradar', pattern: 'ground',  n: 2, interval: 48, x: 130,        hp: 1, speed: 0,   score: 400, shootEvery: 0 },
                { t: 2780, type: 'enemy3', pattern: 'sine',    n: 8, interval: 15, x: 130,      hp: 2, speed: 3.0, score: 200, shootEvery: 75 }
            ],
            midBossAt: 1480,  // このフレームで中ボス演出へ
            bossAt: 3150,
            boss: {
                id: 3, img: 'boss3', name: 'OMEGA CORE',
                hp: 800, score: 20000
            }
        }
    ]
};
