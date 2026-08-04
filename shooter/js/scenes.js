/*
 * scenes.js — タイトル / ステージ / ゲームオーバー / エンディング
 *
 * ゲーム進行: タイトル → STAGE1 → BOSS → STAGE2 → BOSS → STAGE3 → BOSS → エンディング
 */

/* ---------- 共有状態 ---------- */

var GameState = {
    score: 0,
    hiScore: 0,
    lives: 0,
    power: 1,
    stageIdx: 0,

    reset: function () {
        this.score = 0;
        this.lives = CONFIG.PLAYER.lives;
        this.power = 1;
        this.stageIdx = 0;
    },
    addScore: function (n) {
        this.score += n;
        if (this.score > this.hiScore) { this.hiScore = this.score; }
    },
    loadHiScore: function () {
        try {
            this.hiScore = parseInt(localStorage.getItem(CONFIG.HISCORE_KEY), 10) || 0;
        } catch (e) { this.hiScore = 0; }
    },
    saveHiScore: function () {
        try {
            localStorage.setItem(CONFIG.HISCORE_KEY, String(this.hiScore));
        } catch (e) {}
    }
};

/* ---------- 小道具 ---------- */

function makeLabel(text, y, size, color, bold) {
    var l = new Label(text);
    l.x = 0;
    l.y = y;
    l.width = CONFIG.WIDTH;
    l.color = color || '#ffffff';
    l.font = (bold ? 'bold ' : '') + size + 'px "Courier New", monospace';
    l.textAlign = 'center';
    return l;
}

function zeroPad(n, len) {
    return (Array(len + 1).join('0') + n).slice(-len);
}

/* 縦スクロール背景(2枚を継ぎ足しループ) */
function makeScrollBg(scene, key, speed) {
    var meta = ASSETS.img[key];
    var tiles = [];
    for (var i = 0; i < 2; i++) {
        var sp = new Sprite(meta.fw, meta.fh);
        sp.image = imgAsset(key);
        sp.x = 0;
        sp.y = -i * meta.fh;
        scene.addChild(sp);
        tiles.push(sp);
    }
    return {
        speed: speed,
        update: function () {
            for (var i = 0; i < 2; i++) {
                tiles[i].y += this.speed;
                if (tiles[i].y >= meta.fh) { tiles[i].y -= meta.fh * 2; }
            }
        }
    };
}

/*
 * タッチ受け用の透明パッド。
 * enchant はタッチを最前面のエンティティ1つにしか配送しない(バブリングなし)ため、
 * Scene にリスナーを付けても背景スプライトに吸われて届かない。
 * 必ずシーンの一番最後(最前面)に addChild すること。
 * image を持たないスプライトでも当たり判定は幅x高さの矩形全体が有効。
 */
function makeTouchPad(scene) {
    var pad = new Sprite(CONFIG.WIDTH, CONFIG.HEIGHT);
    scene.addChild(pad);
    return pad;
}

/* ---------- タイトル ---------- */

function makeTitleScene() {
    var scene = new Scene();
    scene.backgroundColor = '#000';
    var bg = makeScrollBg(scene, 'bg1', 0.4);

    var title1 = makeLabel(CONFIG.TITLE, 120, 34, '#ffd700', true);
    var title2 = makeLabel(CONFIG.TITLE, 118, 34, '#ff4040', true);   // 影の上に重ねて2色ロゴ風
    scene.addChild(title1);
    scene.addChild(title2);
    scene.addChild(makeLabel('- 8BIT VERTICAL SHOOTER -', 170, 12, '#80c0ff'));

    var prompt = makeLabel('PRESS ANY KEY', 260, 14, '#ffffff', true);
    scene.addChild(prompt);

    scene.addChild(makeLabel('MOVE: ARROWS / WASD   SHOT: Z or SPACE', 330, 10, '#a0a0a0'));
    scene.addChild(makeLabel('P: PAUSE   M: MUTE', 350, 10, '#a0a0a0'));
    scene.addChild(makeLabel('HI-SCORE  ' + zeroPad(GameState.hiScore, 8), 400, 12, '#40ff80'));
    scene.addChild(makeLabel('(C) 2026 MASTERS TEAM', 450, 10, '#606060'));

    var ready = AudioMgr.isUnlocked();
    if (ready) {
        prompt.text = 'PRESS Z TO START';
        AudioMgr.playBgm('title');
    }
    var starting = -1;
    var armed = false;       // ボタンが一度離されるまで開始を受け付けない
    var readyPrev = ready;   // タッチ用: 前フレーム時点で解禁済みだったか

    /* 最初の入力で音を解禁、次の入力で開始(main.js の unlockHandler から呼ばれる) */
    scene.onUnlock = function () {
        if (!ready) {
            ready = true;
            armed = false;   // 解禁に使ったキーを離してから改めて押してもらう
            prompt.text = 'PRESS Z TO START';
            AudioMgr.playBgm('title');
        }
    };

    var startGame = function () {
        if (starting >= 0) { return; }
        starting = 45;
        AudioMgr.playSe('start');
        AudioMgr.stopBgm();
        GameState.reset();
    };

    scene.on('enterframe', function () {
        bg.update();
        if (starting >= 0) {
            prompt.visible = (starting % 6 < 3);   // 開始演出: 高速点滅
            if (--starting <= 0) {
                game.replaceScene(makeStageScene(0));
            }
            return;
        }
        prompt.visible = (scene.age % 60 < 38);
        /* ゲームオーバー等から Z 押しっぱなしで戻ってきた場合の暴発防止 */
        if (!inputShot()) { armed = true; }
        else if (armed && ready) { startGame(); }
        readyPrev = ready;
    });

    var pad = makeTouchPad(scene);
    pad.on('touchstart', function () {
        /* 未解禁時のアンロックは main.js の document リスナーが担当。
           解禁と同時のタップでは開始しない(readyPrev で1フレーム置く) */
        if (readyPrev) { startGame(); }
    });
    return scene;
}

/* ---------- ステージ ---------- */

function makeStageScene(stageIdx) {
    var stage = CONFIG.STAGES[stageIdx];
    GameState.stageIdx = stageIdx;

    var scene = new Scene();
    scene.backgroundColor = '#000';
    scene.paused = false;

    var bg = makeScrollBg(scene, stage.bg, stage.scroll);
    scene.scrollSpeed = stage.scroll;   /* 地上物がこの速度で流れる */

    /* 描画順を決めるグループ */
    var gGround = new Group();          /* 地上物。他のスプライトより奥に描く */
    var gPlayerBullet = new Group();
    var gEnemy = new Group();
    var gItem = new Group();
    var gPlayer = new Group();
    var gEnemyBullet = new Group();
    var gEffect = new Group();
    var gUi = new Group();
    [gGround, gPlayerBullet, gEnemy, gItem, gPlayer, gEnemyBullet, gEffect, gUi]
        .forEach(function (g) { scene.addChild(g); });

    /* エンティティ管理 */
    scene.enemies = [];
    scene.enemyBullets = [];
    scene.playerBullets = [];
    scene.items = [];
    scene.effects = [];
    scene.boss = null;

    scene.addEnemy = function (e) {
        this.enemies.push(e);
        (e.pattern === 'ground' ? gGround : gEnemy).addChild(e);
    };
    scene.addEnemyBullet = function (b) { this.enemyBullets.push(b); gEnemyBullet.addChild(b); };
    scene.addPlayerBullet = function (b) { this.playerBullets.push(b); gPlayerBullet.addChild(b); };
    scene.addItem = function (it) { this.items.push(it); gItem.addChild(it); };
    scene.addEffect = function (fx) { this.effects.push(fx); gEffect.addChild(fx); };

    function updateList(list, group) {
        for (var i = list.length - 1; i >= 0; i--) {
            if (!list[i].update(scene)) {
                (list[i].parentNode || group).removeChild(list[i]);
                list.splice(i, 1);
            }
        }
    }

    /* 自機 */
    var player = new Player();
    scene.player = player;
    gPlayer.addChild(player);

    /* ---------- HUD ---------- */
    var hudBg = new Sprite(CONFIG.WIDTH, 34);
    var hudSurf = new Surface(CONFIG.WIDTH, 34);
    hudSurf.context.fillStyle = '#000000';
    hudSurf.context.fillRect(0, 0, CONFIG.WIDTH, 34);
    hudSurf.context.fillStyle = '#303060';
    hudSurf.context.fillRect(0, 32, CONFIG.WIDTH, 2);
    hudBg.image = hudSurf;
    gUi.addChild(hudBg);

    var scoreLabel = new Label('');
    scoreLabel.x = 6; scoreLabel.y = 4; scoreLabel.width = 200;
    scoreLabel.color = '#ffffff';
    scoreLabel.font = 'bold 11px "Courier New", monospace';
    gUi.addChild(scoreLabel);

    var hiLabel = new Label('');
    hiLabel.x = 6; hiLabel.y = 19; hiLabel.width = 200;
    hiLabel.color = '#40ff80';
    hiLabel.font = 'bold 11px "Courier New", monospace';
    gUi.addChild(hiLabel);

    var livesLabel = new Label('');
    livesLabel.x = 210; livesLabel.y = 4; livesLabel.width = 110;
    livesLabel.color = '#ff8080';
    livesLabel.font = 'bold 11px "Courier New", monospace';
    gUi.addChild(livesLabel);

    var powerLabel = new Label('');
    powerLabel.x = 210; powerLabel.y = 19; powerLabel.width = 110;
    powerLabel.color = '#ffd700';
    powerLabel.font = 'bold 11px "Courier New", monospace';
    gUi.addChild(powerLabel);

    function updateHud() {
        scoreLabel.text = 'SC ' + zeroPad(GameState.score, 8);
        hiLabel.text = 'HI ' + zeroPad(GameState.hiScore, 8);
        livesLabel.text = 'LIVES ' + Math.max(0, GameState.lives);
        powerLabel.text = 'POWER ' + GameState.power + '/' + CONFIG.PLAYER.maxPower;
    }
    updateHud();

    /* ボスHPバー */
    var hpBar = new Sprite(CONFIG.WIDTH, 10);
    var hpSurf = new Surface(CONFIG.WIDTH, 10);
    hpBar.image = hpSurf;
    hpBar.y = 34;
    hpBar.visible = false;
    gUi.addChild(hpBar);

    function drawHpBar() {
        var c = hpSurf.context;
        c.clearRect(0, 0, CONFIG.WIDTH, 10);
        c.fillStyle = '#400000';
        c.fillRect(2, 2, CONFIG.WIDTH - 4, 6);
        if (scene.boss && scene.boss.maxHp > 0) {
            var w = Math.max(0, (CONFIG.WIDTH - 4) * scene.boss.hp / scene.boss.maxHp);
            c.fillStyle = '#ff3030';
            c.fillRect(2, 2, w, 6);
        }
    }

    /* 中央メッセージ(ステージ名 / WARNING / STAGE CLEAR / PAUSE) */
    var centerMsg = makeLabel(stage.name, 200, 24, '#ffffff', true);
    var subMsg = makeLabel(stage.subtitle, 235, 13, '#80c0ff');
    gUi.addChild(centerMsg);
    gUi.addChild(subMsg);

    var pauseMsg = makeLabel('PAUSE', 220, 22, '#ffff80', true);
    pauseMsg.visible = false;
    gUi.addChild(pauseMsg);
    scene.pauseMsg = pauseMsg;

    /* ---------- ステージ進行 ---------- */
    var t = 0;                     // ステージ経過フレーム
    var state = 'intro';           // intro -> play -> warning -> boss -> clear
    var stateTimer = 150;
    var spawners = [];             // 実行中の編隊
    var pendingWaves = stage.waves.slice();
    var midBossDone = false;       // このステージの中ボスを消化したか
    var midBossMsg = 0;            // ボーナス表示の残りフレーム
    var deathTimer = -1;           // 自機死亡からの復帰カウンタ
    var gameOverTimer = -1;

    AudioMgr.playBgm(stage.bgm);

    function runSpawners() {
        /* 新しい wave の開始 */
        while (pendingWaves.length > 0 && pendingWaves[0].t <= t) {
            var w = pendingWaves.shift();
            spawners.push({ wave: w, spawned: 0, timer: 0 });
        }
        /* 実行中の編隊から敵を出す */
        for (var i = spawners.length - 1; i >= 0; i--) {
            var s = spawners[i];
            if (--s.timer <= 0) {
                var w2 = s.wave;
                var bx = (w2.x === 'random') ? rand(30, CONFIG.WIDTH - 30) : w2.x;
                var e = new Enemy(w2, bx);
                if (w2.drop && s.spawned === w2.n - 1) { e.drop = true; }
                scene.addEnemy(e);
                s.spawned++;
                s.timer = w2.interval;
                if (s.spawned >= w2.n) { spawners.splice(i, 1); }
            }
        }
    }

    function clearCenterMsg() {
        centerMsg.visible = false;
        subMsg.visible = false;
    }

    /* ---------- 中ボス ---------- */
    function startMidBoss() {
        state = 'midboss';
        clearCenterMsg();                    // ステージ名などが出ていたら消す
        AudioMgr.playBgm('midboss');        // 不穏なBGMへ
        scene.midBoss = new MidBoss();
        gEnemy.addChild(scene.midBoss);
    }

    function endMidBoss() {
        gEnemy.removeChild(scene.midBoss);
        scene.midBoss = null;
        midBossDone = true;
        state = 'play';
        AudioMgr.playBgm(stage.bgm);         // ステージBGMへ戻す
    }

    /* 中ボスを倒したときの加点と演出 */
    function onMidBossHit(result) {
        var cfg = CONFIG.MIDBOSS;
        if (result === 'bonus') {
            GameState.addScore(cfg.bonusScore);
            centerMsg.text = 'PERFECT!';
            centerMsg.color = '#ffd700';
            subMsg.text = 'BONUS ' + cfg.bonusScore;
            subMsg.color = '#ffffff';
            centerMsg.visible = true;
            subMsg.visible = true;
            midBossMsg = 150;
        } else if (result === 'normal') {
            GameState.addScore(cfg.normalScore);
        }
    }

    function startWarning() {
        state = 'warning';
        stateTimer = 160;
        spawners = [];
        pendingWaves = [];
        AudioMgr.stopBgm();
        AudioMgr.playSe('start');
        centerMsg.text = 'WARNING!!';
        centerMsg.color = '#ff3030';
        centerMsg.visible = true;
        subMsg.text = stage.boss.name + ' APPROACHING';
        subMsg.color = '#ff8080';
        subMsg.visible = true;
    }

    function startBoss() {
        state = 'boss';
        centerMsg.visible = false;
        subMsg.visible = false;
        AudioMgr.playBgm('boss');
        scene.boss = new Boss(stage.boss);
        gEnemy.addChild(scene.boss);
        hpBar.visible = true;
    }

    scene.onBossDead = function () {
        var boss = scene.boss;
        gEnemy.removeChild(boss);
        scene.boss = null;
        hpBar.visible = false;
        GameState.addScore(stage.boss.score);
        AudioMgr.stopBgm();
        AudioMgr.playSe('clear');
        state = 'clear';
        stateTimer = 240;
        centerMsg.text = 'STAGE CLEAR!';
        centerMsg.color = '#ffd700';
        centerMsg.visible = true;
        subMsg.text = 'BONUS ' + stage.boss.score;
        subMsg.color = '#ffffff';
        subMsg.visible = true;
        /* 残った敵弾を消してあげる */
        scene.enemyBullets.forEach(function (b) { gEnemyBullet.removeChild(b); });
        scene.enemyBullets = [];
    };

    function killPlayer() {
        if (!player.alive || player.invincible > 0) { return; }
        player.alive = false;
        player.visible = false;
        player.touchTarget = null;
        scene.addEffect(new Explosion(player.cx(), player.cy()));
        AudioMgr.playSe('player_death');
        GameState.lives--;
        updateHud();
        if (GameState.lives < 0) {
            gameOverTimer = 100;
        } else {
            deathTimer = 70;
        }
    }

    function respawn() {
        GameState.power = Math.max(1, GameState.power - 1);
        player.setCenter(CONFIG.WIDTH / 2, CONFIG.HEIGHT - 50);
        player.alive = true;
        player.visible = true;
        player.invincible = CONFIG.PLAYER.respawnInvincible;
        updateHud();
    }

    /* ---------- 衝突判定 ---------- */
    function collide() {
        var i, j, b, e;

        /* 自機弾 vs 敵 */
        outer:
        for (i = scene.playerBullets.length - 1; i >= 0; i--) {
            b = scene.playerBullets[i];
            for (j = scene.enemies.length - 1; j >= 0; j--) {
                e = scene.enemies[j];
                if (hitCircle(b.cx(), b.cy(), b.r, e.cx(), e.cy(), e.r)) {
                    gPlayerBullet.removeChild(b);
                    scene.playerBullets.splice(i, 1);
                    if (e.damage(1)) {
                        scene.addEffect(new Explosion(e.cx(), e.cy()));
                        AudioMgr.playSe('explosion');
                        GameState.addScore(e.score);
                        if (e.drop) { scene.addItem(new PowerUp(e.cx(), e.cy())); }
                        e.parentNode.removeChild(e);
                        scene.enemies.splice(j, 1);
                    } else {
                        AudioMgr.playSe('hit');
                    }
                    continue outer;
                }
            }
            /* 自機弾 vs ボス */
            if (scene.boss && scene.boss.state === 'fight' &&
                hitCircle(b.cx(), b.cy(), b.r, scene.boss.cx(), scene.boss.cy(), scene.boss.r)) {
                gPlayerBullet.removeChild(b);
                scene.playerBullets.splice(i, 1);
                scene.boss.damage(1);
                continue;
            }
            /*
             * 自機弾 vs 中ボス。
             * パーツは常に無敵の障害物なので、先に判定してショットを弾く
             * (ダメージにはならない)。ダメージが通るのはコアだけ。
             */
            if (scene.midBoss) {
                var mb = scene.midBoss, pt = mb.partTargets(), m, blocked = false;
                for (m = 0; m < pt.length; m++) {
                    if (!hitCircle(b.cx(), b.cy(), b.r, pt[m].x, pt[m].y, pt[m].r)) { continue; }
                    mb.deflect(pt[m].idx);
                    gPlayerBullet.removeChild(b);
                    scene.playerBullets.splice(i, 1);
                    blocked = true;
                    break;
                }
                if (!blocked && mb.coreVulnerable()) {
                    var ct = mb.coreTarget();
                    if (hitCircle(b.cx(), b.cy(), b.r, ct.x, ct.y, ct.r)) {
                        gPlayerBullet.removeChild(b);
                        scene.playerBullets.splice(i, 1);
                        onMidBossHit(mb.damage(1));
                    }
                }
            }
        }

        if (!player.alive) { return; }
        var px = player.cx(), py = player.cy(), pr = CONFIG.PLAYER.hitR;

        /* 敵弾 vs 自機 */
        if (player.invincible <= 0) {
            for (i = scene.enemyBullets.length - 1; i >= 0; i--) {
                b = scene.enemyBullets[i];
                if (hitCircle(b.cx(), b.cy(), b.r, px, py, pr)) {
                    gEnemyBullet.removeChild(b);
                    scene.enemyBullets.splice(i, 1);
                    killPlayer();
                    return;
                }
            }
            /* 敵本体 vs 自機 */
            for (i = scene.enemies.length - 1; i >= 0; i--) {
                e = scene.enemies[i];
                if (hitCircle(e.cx(), e.cy(), e.r * 0.8, px, py, pr + 2)) {
                    scene.addEffect(new Explosion(e.cx(), e.cy()));
                    e.parentNode.removeChild(e);
                    scene.enemies.splice(i, 1);
                    killPlayer();
                    return;
                }
            }
            /* ボス本体 vs 自機 */
            if (scene.boss && scene.boss.state === 'fight' &&
                hitCircle(scene.boss.cx(), scene.boss.cy(), scene.boss.r * 0.8, px, py, pr + 2)) {
                killPlayer();
                return;
            }
            /*
             * 中ボス vs 自機。
             * パーツは静止した時点から障害物になるので、触れると自機がやられる。
             * コアは攻撃が通る状態(=合体開始後)のみ当たる。飛来中は判定なし。
             */
            if (scene.midBoss) {
                var mb2 = scene.midBoss, pt2 = mb2.partTargets(), mi;
                for (mi = 0; mi < pt2.length; mi++) {
                    if (hitCircle(pt2[mi].x, pt2[mi].y, pt2[mi].r * 0.8, px, py, pr + 2)) {
                        killPlayer();
                        return;
                    }
                }
                if (mb2.coreVulnerable()) {
                    var ct2 = mb2.coreTarget();
                    if (hitCircle(ct2.x, ct2.y, ct2.r * 0.8, px, py, pr + 2)) {
                        killPlayer();
                        return;
                    }
                }
            }
        }

        /* アイテム回収 */
        for (i = scene.items.length - 1; i >= 0; i--) {
            var it = scene.items[i];
            if (hitCircle(it.cx(), it.cy(), it.r, px, py, pr + 14)) {
                gItem.removeChild(it);
                scene.items.splice(i, 1);
                AudioMgr.playSe('powerup');
                if (GameState.power < CONFIG.PLAYER.maxPower) {
                    GameState.power++;
                    GameState.addScore(500);
                } else {
                    GameState.addScore(1000);
                }
                updateHud();
            }
        }
    }

    /* ---------- メインループ ---------- */
    scene.on('enterframe', function () {
        if (scene.paused) { return; }
        bg.update();

        /* 進行状態 */
        if (state === 'intro') {
            if (--stateTimer <= 0) {
                state = 'play';
                centerMsg.visible = false;
                subMsg.visible = false;
            }
        } else if (state === 'play') {
            t++;
            runSpawners();
            if (!midBossDone && stage.midBossAt && t >= stage.midBossAt) {
                startMidBoss();
            } else if (t >= stage.bossAt && scene.enemies.length === 0) {
                startWarning();
            }
        } else if (state === 'midboss') {
            /* 中ボス中は新しい編隊を出さない(t も進めない)。
               既に出ている敵と地上物はそのまま流れていく */
        } else if (state === 'warning') {
            centerMsg.visible = (stateTimer % 20 < 12);
            subMsg.visible = centerMsg.visible;
            if (--stateTimer <= 0) { startBoss(); }
        } else if (state === 'clear') {
            if (--stateTimer <= 0) {
                if (stageIdx + 1 < CONFIG.STAGES.length) {
                    game.replaceScene(makeStageScene(stageIdx + 1));
                } else {
                    GameState.saveHiScore();
                    game.replaceScene(makeEndingScene());
                }
                return;
            }
        }

        /* ボーナス表示は状態に関わらず消す(撃破で play に戻っても残らないように) */
        if (midBossMsg > 0 && --midBossMsg === 0) { clearCenterMsg(); }

        /* 死亡・復活・ゲームオーバー */
        if (deathTimer > 0 && --deathTimer === 0) { respawn(); }
        if (gameOverTimer > 0 && --gameOverTimer === 0) {
            AudioMgr.stopBgm();
            GameState.saveHiScore();
            game.replaceScene(makeGameOverScene());
            return;
        }

        /* エンティティ更新 */
        player.update(scene);
        updateList(scene.enemies, gEnemy);
        updateList(scene.playerBullets, gPlayerBullet);
        updateList(scene.enemyBullets, gEnemyBullet);
        updateList(scene.items, gItem);
        updateList(scene.effects, gEffect);
        if (scene.boss) {
            if (!scene.boss.update(scene)) { /* onBossDead 内で後処理済み */ }
        }
        if (scene.midBoss) {
            if (!scene.midBoss.update(scene)) { endMidBoss(); }
        }

        collide();
        if (scene.boss) { drawHpBar(); }
        updateHud();
    });

    /* デバッグ用フック(main.js の ?debug=1 から使う) */
    scene.debug = {
        /* 中ボス演出を即開始する */
        startMidBoss: function () {
            if (scene.midBoss || midBossDone) { return; }
            startMidBoss();
        },
        skipToBoss: function () {
            if (state !== 'play' && state !== 'intro') { return; }
            state = 'play';
            t = stage.bossAt;
            pendingWaves = [];
            spawners = [];
            scene.enemies.forEach(function (e) { e.parentNode.removeChild(e); });
            scene.enemies = [];
            centerMsg.visible = false;
            subMsg.visible = false;
        },
        killBoss: function () {
            if (scene.boss && scene.boss.state === 'fight') {
                scene.boss.damage(scene.boss.hp);
            }
        }
    };

    /* タッチ操作(最前面の透明パッドで受ける) */
    var pad = makeTouchPad(scene);
    pad.on('touchstart', function (ev) {
        player.touchTarget = { x: ev.x, y: ev.y };
    });
    pad.on('touchmove', function (ev) {
        player.touchTarget = { x: ev.x, y: ev.y };
    });
    pad.on('touchend', function () {
        player.touchTarget = null;
    });

    return scene;
}

/* ---------- ゲームオーバー ---------- */

function makeGameOverScene() {
    var scene = new Scene();
    scene.backgroundColor = '#000';

    scene.addChild(makeLabel('GAME OVER', 160, 30, '#ff3030', true));
    scene.addChild(makeLabel('SCORE  ' + zeroPad(GameState.score, 8), 240, 14, '#ffffff'));
    scene.addChild(makeLabel('HI     ' + zeroPad(GameState.hiScore, 8), 265, 14, '#40ff80'));
    var prompt = makeLabel('PRESS Z FOR TITLE', 340, 13, '#ffffff', true);
    scene.addChild(prompt);

    var wait = 45;   // 押しっぱなし誤爆防止
    scene.on('enterframe', function () {
        prompt.visible = (scene.age % 60 < 38);
        if (wait > 0) { wait--; return; }
        if (inputShot()) {
            game.replaceScene(makeTitleScene());
        }
    });
    var pad = makeTouchPad(scene);
    pad.on('touchstart', function () {
        if (wait <= 0) { game.replaceScene(makeTitleScene()); }
    });
    return scene;
}

/* ---------- エンディング ---------- */

function makeEndingScene() {
    var scene = new Scene();
    scene.backgroundColor = '#000';
    var bg = makeScrollBg(scene, 'bg1', 0.3);

    AudioMgr.playBgm('ending');

    /* 自機がゆっくり飛んでいく */
    var ship = new Sprite(ASSETS.img.player.fw, ASSETS.img.player.fh);
    ship.image = imgAsset('player');
    ship.frame = flickFrames(4);
    ship.x = CONFIG.WIDTH / 2 - ship.width / 2;
    ship.y = CONFIG.HEIGHT - 90;
    scene.addChild(ship);

    /* スタッフロール */
    var credits = new Group();
    var lineH = 24;
    CONFIG.CREDITS.forEach(function (line, i) {
        var big = (i === 0);
        var l = makeLabel(line, i * lineH, big ? 20 : 13,
                          big ? '#ffd700' : '#ffffff', big);
        credits.addChild(l);
    });
    credits.y = CONFIG.HEIGHT + 20;
    scene.addChild(credits);

    var totalH = CONFIG.CREDITS.length * lineH;
    var finished = false;
    var endLabel = makeLabel('THE END', 190, 26, '#ffd700', true);
    var scoreLabel = makeLabel('FINAL SCORE  ' + zeroPad(GameState.score, 8), 250, 13, '#ffffff');
    var prompt = makeLabel('PRESS Z FOR TITLE', 320, 12, '#a0a0a0');
    endLabel.visible = scoreLabel.visible = prompt.visible = false;
    scene.addChild(endLabel);
    scene.addChild(scoreLabel);
    scene.addChild(prompt);

    var wait = 60;
    scene.on('enterframe', function () {
        bg.update();
        if (ship.y > 120) { ship.y -= 0.4; }

        if (!finished) {
            credits.y -= 0.55;
            if (credits.y + totalH < CONFIG.HEIGHT / 2 - 40) {
                finished = true;
                scene.removeChild(credits);
                endLabel.visible = true;
                scoreLabel.visible = true;
            }
        } else {
            prompt.visible = (scene.age % 60 < 38);
            if (wait > 0) { wait--; return; }
            if (inputShot()) {
                AudioMgr.stopBgm();
                game.replaceScene(makeTitleScene());
            }
        }
    });
    var pad = makeTouchPad(scene);
    pad.on('touchstart', function () {
        if (finished && wait <= 0) {
            AudioMgr.stopBgm();
            game.replaceScene(makeTitleScene());
        }
    });
    return scene;
}
