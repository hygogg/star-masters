/*
 * entities.js — 自機・敵・ボス・弾・爆発・アイテム
 *
 * 各エンティティは enchant.Sprite のサブクラス。
 * 毎フレームの挙動は StageScene が update() を呼ぶ方式(実行順を制御するため)。
 */

/* ---------- ユーティリティ ---------- */

function imgAsset(key) {
    return game.assets[ASSETS.img[key].path];
}

function rand(a, b) {
    return a + Math.random() * (b - a);
}

/* 円同士の当たり判定 */
function hitCircle(ax, ay, ar, bx, by, br) {
    var dx = ax - bx, dy = ay - by, r = ar + br;
    return dx * dx + dy * dy < r * r;
}

/* コマ番号配列を作る: 2コマを ticks フレームずつ交互に */
function flickFrames(ticks) {
    var arr = [];
    for (var i = 0; i < ticks; i++) { arr.push(0); }
    for (var j = 0; j < ticks; j++) { arr.push(1); }
    return arr;
}

/* ショットボタン(Z / Space / X はそれぞれ別ボタン名に割り当ててある) */
function inputShot() {
    return game.input.a || game.input.b || game.input.c;
}

/* ---------- 自機 ---------- */

var Player = Class.create(Sprite, {
    initialize: function () {
        Sprite.call(this, ASSETS.img.player.fw, ASSETS.img.player.fh);
        this.image = imgAsset('player');
        this.frame = flickFrames(4);
        this.alive = true;
        this.cooldown = 0;
        this.invincible = CONFIG.PLAYER.respawnInvincible;
        this.touchTarget = null;   // タッチ操作の目標座標
        this.setCenter(CONFIG.WIDTH / 2, CONFIG.HEIGHT - 50);
    },
    setCenter: function (cx, cy) {
        this.x = cx - this.width / 2;
        this.y = cy - this.height / 2;
    },
    cx: function () { return this.x + this.width / 2; },
    cy: function () { return this.y + this.height / 2; },

    update: function (scene) {
        if (!this.alive) { return; }
        var sp = CONFIG.PLAYER.speed;
        var input = game.input;

        if (input.left || input.left2)   { this.x -= sp; }
        if (input.right || input.right2) { this.x += sp; }
        if (input.up || input.up2)       { this.y -= sp; }
        if (input.down || input.down2)   { this.y += sp; }

        /* タッチ操作: 指の少し上に追従 */
        if (this.touchTarget) {
            var tx = this.touchTarget.x - this.width / 2;
            var ty = this.touchTarget.y - 40 - this.height / 2;
            this.x += Math.max(-6, Math.min(6, tx - this.x));
            this.y += Math.max(-6, Math.min(6, ty - this.y));
        }

        this.x = Math.max(0, Math.min(CONFIG.WIDTH - this.width, this.x));
        this.y = Math.max(36, Math.min(CONFIG.HEIGHT - this.height, this.y));

        /* ショット(タッチ中はオート連射) */
        if (this.cooldown > 0) { this.cooldown--; }
        if ((inputShot() || this.touchTarget) && this.cooldown <= 0) {
            this.shoot(scene);
            this.cooldown = CONFIG.PLAYER.shotInterval;
        }

        /* 無敵時間は点滅 */
        if (this.invincible > 0) {
            this.invincible--;
            this.opacity = (this.invincible % 8 < 4) ? 0.35 : 1;
        } else {
            this.opacity = 1;
        }
    },

    shoot: function (scene) {
        var cx = this.cx(), top = this.y + 2;
        var power = GameState.power;
        scene.addPlayerBullet(new PlayerBullet(cx, top, 0));
        if (power >= 2) {
            scene.addPlayerBullet(new PlayerBullet(cx - 11, top + 6, 0));
            scene.addPlayerBullet(new PlayerBullet(cx + 11, top + 6, 0));
        }
        if (power >= 3) {
            scene.addPlayerBullet(new PlayerBullet(cx - 14, top + 10, -1.8));
            scene.addPlayerBullet(new PlayerBullet(cx + 14, top + 10, 1.8));
        }
        AudioMgr.playSe('shot');
    }
});

/* ---------- 弾 ---------- */

var PlayerBullet = Class.create(Sprite, {
    initialize: function (cx, cy, vx) {
        Sprite.call(this, ASSETS.img.bullet_player.fw, ASSETS.img.bullet_player.fh);
        this.image = imgAsset('bullet_player');
        this.x = cx - this.width / 2;
        this.y = cy - this.height / 2;
        this.vx = vx;
        this.vy = -CONFIG.BULLET.playerSpeed;
        this.r = 5;
    },
    cx: function () { return this.x + this.width / 2; },
    cy: function () { return this.y + this.height / 2; },
    update: function () {
        this.x += this.vx;
        this.y += this.vy;
        return this.y > -24 && this.x > -24 && this.x < CONFIG.WIDTH + 24;
    }
});

var EnemyBullet = Class.create(Sprite, {
    initialize: function (cx, cy, angle, speed) {
        Sprite.call(this, ASSETS.img.bullet_enemy.fw, ASSETS.img.bullet_enemy.fh);
        this.image = imgAsset('bullet_enemy');
        this.x = cx - this.width / 2;
        this.y = cy - this.height / 2;
        this.vx = Math.cos(angle) * speed;
        this.vy = Math.sin(angle) * speed;
        this.r = 3.5;
    },
    cx: function () { return this.x + this.width / 2; },
    cy: function () { return this.y + this.height / 2; },
    update: function () {
        this.x += this.vx;
        this.y += this.vy;
        return this.y > -24 && this.y < CONFIG.HEIGHT + 24 &&
               this.x > -24 && this.x < CONFIG.WIDTH + 24;
    }
});

/* 弾幕ヘルパー(すべて scene 経由で追加) */

function fireAimed(scene, x, y, count, spread, speed) {
    var p = scene.player;
    if (!p || !p.alive) { return; }
    var base = Math.atan2(p.cy() - y, p.cx() - x);
    var start = base - spread * (count - 1) / 2;
    for (var i = 0; i < count; i++) {
        scene.addEnemyBullet(new EnemyBullet(x, y, start + spread * i, speed));
    }
}

function fireRing(scene, x, y, count, speed, offset) {
    for (var i = 0; i < count; i++) {
        var a = offset + i * Math.PI * 2 / count;
        scene.addEnemyBullet(new EnemyBullet(x, y, a, speed));
    }
}

/* ---------- 敵(ザコ・中型) ---------- */

var Enemy = Class.create(Sprite, {
    /* spec: config.js の wave 定義 + baseX */
    initialize: function (spec, baseX) {
        var meta = ASSETS.img[spec.type];
        Sprite.call(this, meta.fw, meta.fh);
        this.image = imgAsset(spec.type);
        this.frame = flickFrames(8);
        this.spec = spec;
        this.hp = spec.hp;
        this.score = spec.score;
        this.pattern = spec.pattern;
        this.speed = spec.speed;
        this.baseX = baseX;
        this.drop = false;                 // 編隊最後の1機に scene が付与
        this.shootTimer = spec.shootEvery > 0 ?
            Math.floor(rand(20, spec.shootEvery)) : -1;
        this.x = baseX - meta.fw / 2;
        this.y = -meta.fh;
        this.vx = 0;
        this.vy = spec.speed;
        this.r = meta.fw * 0.36;
        this.flash = 0;
        /* enchant の age はポーズ中も進んでしまうため、自前のカウンタを使う */
        this.t = 0;

        if (this.pattern === 'swoopL') { this.vx = 0.6;  this.vy = spec.speed * 1.5; }
        if (this.pattern === 'swoopR') { this.vx = -0.6; this.vy = spec.speed * 1.5; }
    },
    cx: function () { return this.x + this.width / 2; },
    cy: function () { return this.y + this.height / 2; },

    update: function (scene) {
        var t = ++this.t;
        switch (this.pattern) {
        case 'sine':
            this.y += this.speed * 0.85;
            this.x = this.baseX - this.width / 2 + Math.sin(t * 0.055) * 46;
            break;
        case 'swoopL':
            if (t > 40) { this.vx += 0.12; this.vy = Math.max(0.6, this.vy - 0.05); }
            this.x += this.vx; this.y += this.vy;
            break;
        case 'swoopR':
            if (t > 40) { this.vx -= 0.12; this.vy = Math.max(0.6, this.vy - 0.05); }
            this.x += this.vx; this.y += this.vy;
            break;
        /*
         * 地上物。背景と同じ速度で流れるので「地面に固定されている」ように見える。
         * 空中物との違いは移動だけで、当たり判定・破壊のされ方は同じ
         * (通常ショットで壊せる)。
         */
        case 'ground':
            this.y += scene.scrollSpeed;
            break;
        case 'hover':
            if (this.y < 90) {
                this.y += this.speed;
            } else if (t < 480) {
                this.x = this.baseX - this.width / 2 + Math.sin(t * 0.03) * 24;
            } else {
                this.y += (t - 480) * 0.02 + 0.5;
            }
            break;
        default: /* straight */
            this.y += this.speed;
        }

        /* 自機狙い弾 */
        if (this.shootTimer >= 0 && this.cy() > 8 && this.cy() < 360) {
            if (--this.shootTimer <= 0) {
                this.shootTimer = this.spec.shootEvery;
                fireAimed(scene, this.cx(), this.cy() + 8, 1, 0,
                          CONFIG.BULLET.enemySpeed + this.speed * 0.3);
            }
        }

        if (this.flash > 0) {
            this.flash--;
            this.opacity = 0.4;
        } else {
            this.opacity = 1;
        }

        /* 画面外に出たら消す */
        return this.y < CONFIG.HEIGHT + 48 && this.x > -80 && this.x < CONFIG.WIDTH + 80 &&
               this.y > -160;
    },

    /* 戻り値: 撃破したら true */
    damage: function (n) {
        this.hp -= n;
        this.flash = 3;
        return this.hp <= 0;
    }
});

/* ---------- ボス ---------- */

var Boss = Class.create(Sprite, {
    initialize: function (spec) {
        var meta = ASSETS.img[spec.img];
        Sprite.call(this, meta.fw, meta.fh);
        this.image = imgAsset(spec.img);
        this.frame = flickFrames(10);
        this.spec = spec;
        this.hp = spec.hp;
        this.maxHp = spec.hp;
        this.state = 'enter';      // enter -> fight -> dying
        this.fightAge = 0;
        this.dyingAge = 0;
        this.spiralAngle = 0;
        this.flash = 0;
        this.x = CONFIG.WIDTH / 2 - meta.fw / 2;
        this.y = -meta.fh - 10;
        this.r = meta.fw * 0.38;
    },
    cx: function () { return this.x + this.width / 2; },
    cy: function () { return this.y + this.height / 2; },
    phase: function () { return this.hp <= this.maxHp / 2 ? 2 : 1; },

    update: function (scene) {
        if (this.state === 'enter') {
            this.y += 1.2;
            if (this.y >= 40) { this.state = 'fight'; }
        } else if (this.state === 'fight') {
            this.fightAge++;
            this.move();
            this.attack(scene);
        } else if (this.state === 'dying') {
            this.dyingAge++;
            this.x += rand(-3, 3);
            if (this.dyingAge % 8 === 0) {
                scene.addEffect(new Explosion(
                    this.cx() + rand(-40, 40), this.cy() + rand(-40, 40)));
                AudioMgr.playSe('explosion');
            }
            this.opacity = 1 - this.dyingAge / 110;
            if (this.dyingAge >= 110) {
                scene.onBossDead();
                return false;
            }
        }

        if (this.flash > 0) {
            this.flash--;
            if (this.state === 'fight') { this.opacity = 0.5; }
        } else if (this.state !== 'dying') {
            this.opacity = 1;
        }
        return true;
    },

    move: function () {
        var t = this.fightAge;
        var w = this.width;
        switch (this.spec.id) {
        case 1:
            this.x = CONFIG.WIDTH / 2 - w / 2 + Math.sin(t * 0.02) * 80;
            this.y = 40 + Math.sin(t * 0.013) * 12;
            break;
        case 2:
            this.x = CONFIG.WIDTH / 2 - w / 2 + Math.sin(t * 0.033) * 100;
            this.y = 40 + Math.sin(t * 0.021) * 18;
            break;
        case 3:
            this.x = CONFIG.WIDTH / 2 - w / 2 + Math.sin(t * 0.012) * 60;
            this.y = 40 + Math.sin(t * 0.017) * 10;
            break;
        }
    },

    attack: function (scene) {
        /* 弾数が多すぎるときは追加発射を抑制(処理落ち・理不尽防止) */
        if (scene.enemyBullets.length > 140) { return; }
        var cx = this.cx(), cy = this.cy() + 20;
        var t = this.fightAge;
        var phase2 = this.phase() === 2;

        switch (this.spec.id) {
        case 1:
            if (!phase2) {
                var c1 = t % 300;
                if (c1 === 30 || c1 === 60 || c1 === 90) { fireAimed(scene, cx, cy, 3, 0.26, 3.0); }
                if (c1 === 200) { fireRing(scene, cx, cy, 16, 2.2, rand(0, Math.PI)); }
            } else {
                var c2 = t % 260;
                if (c2 === 20 || c2 === 50 || c2 === 80 || c2 === 110) { fireAimed(scene, cx, cy, 5, 0.24, 3.2); }
                if (c2 === 180) { fireRing(scene, cx, cy, 20, 2.5, rand(0, Math.PI)); }
            }
            break;

        case 2:
            var lx = this.x + 14, rx = this.x + this.width - 14, wy = this.y + 60;
            if (!phase2) {
                var d1 = t % 240;
                if (d1 % 20 === 0 && d1 <= 100 && d1 > 0) {
                    fireAimed(scene, lx, wy, 1, 0, 3.3);
                    fireAimed(scene, rx, wy, 1, 0, 3.3);
                }
                if (d1 === 160) { fireRing(scene, cx, cy, 14, 2.4, rand(0, Math.PI)); }
            } else {
                if (t % 6 === 0) {
                    this.spiralAngle += 0.23;
                    scene.addEnemyBullet(new EnemyBullet(cx, cy, this.spiralAngle, 2.6));
                    scene.addEnemyBullet(new EnemyBullet(cx, cy, this.spiralAngle + Math.PI, 2.6));
                }
                if (t % 70 === 0) { fireAimed(scene, cx, cy, 3, 0.3, 3.4); }
            }
            break;

        case 3:
            if (!phase2) {
                var e1 = t % 330;
                if (e1 === 30) { fireRing(scene, cx, cy, 20, 2.3, 0); }
                if (e1 >= 90 && e1 <= 180 && e1 % 8 === 0) {
                    this.spiralAngle += 0.31;
                    scene.addEnemyBullet(new EnemyBullet(cx, cy, this.spiralAngle, 2.5));
                }
                if (e1 === 240 || e1 === 270) { fireAimed(scene, cx, cy, 5, 0.22, 3.2); }
            } else {
                var e2 = t % 300;
                if (e2 === 20) { fireRing(scene, cx, cy, 24, 2.4, 0); }
                if (e2 === 90) { fireRing(scene, cx, cy, 24, 2.4, Math.PI / 24); }
                if (e2 >= 120 && e2 <= 240 && e2 % 7 === 0) {
                    this.spiralAngle += 0.29;
                    scene.addEnemyBullet(new EnemyBullet(cx, cy, this.spiralAngle, 2.7));
                    scene.addEnemyBullet(new EnemyBullet(cx, cy, this.spiralAngle + Math.PI, 2.7));
                }
                if (e2 === 260) { fireAimed(scene, cx, cy, 7, 0.2, 3.4); }
            }
            break;
        }
    },

    /* 戻り値: 撃破したら true */
    damage: function (n) {
        if (this.state !== 'fight') { return false; }
        this.hp -= n;
        this.flash = 3;
        AudioMgr.playSe('hit');
        if (this.hp <= 0) {
            this.hp = 0;
            this.state = 'dying';
            AudioMgr.playSe('boss_explosion');
            return true;
        }
        return false;
    }
});

/* ---------- 中ボス ---------- */

/*
 * コア1つ + 四方(上下左右)のパーツ4つで構成される中ボス。
 *
 *   enter … コアが画面上部へ降りてくる           (無敵)
 *   hold  … 四方にパーツが出現して静止           (無敵) CONFIG.MIDBOSS.holdFrames
 *   merge … パーツがコアへ集まる                 (有効) CONFIG.MIDBOSS.mergeFrames
 *           ここで hp 発当てて壊すと bonusScore + ファンファーレ
 *   full  … 合体完了。hpを戻して通常戦闘          (有効)
 *           壊すと normalScore。fullTimeout で去る
 *   dying … 爆発演出
 *
 * 当たり判定はコアと4パーツそれぞれに持たせ、ダメージは1つのHPに集約する
 * (どこを撃っても「八発当てれば壊れる」)。
 */
var MIDBOSS_DIRS = [
    [ 0, -1],   /* 上 */
    [ 0,  1],   /* 下 */
    [-1,  0],   /* 左 */
    [ 1,  0]    /* 右 */
];

var MidBoss = Class.create(Group, {
    initialize: function () {
        var cfg = CONFIG.MIDBOSS, i, p;
        Group.call(this);

        this.cfg = cfg;

        /*
         * パーツを先に addChild してコアを後にする = パーツがコアの下に描かれる。
         * こうするとコアの装甲リングとソケットの爪がパーツの上に残り、
         * 「掴んで固定している」ように見える。
         */
        this.parts = [];
        for (i = 0; i < 4; i++) {
            p = new Sprite(ASSETS.img.midpart.fw, ASSETS.img.midpart.fh);
            p.image = imgAsset('midpart');
            p.frame = flickFrames(6);
            p.visible = false;
            p.flash = 0;
            this.addChild(p);
            this.parts.push(p);
        }

        this.core = new Sprite(ASSETS.img.midcore.fw, ASSETS.img.midcore.fh);
        this.core.image = imgAsset('midcore');
        this.core.frame = flickFrames(8);
        this.addChild(this.core);

        this.state = 'enter';
        this.t = 0;
        this.hp = cfg.hpMerge;
        this.flash = 0;
        this.shootTimer = cfg.shootEvery;
        this.result = null;          /* 'bonus' | 'normal' | 'escaped' */
        this.partsSolid = false;     /* 静止してから当たり判定が生まれる */

        /* コアは画面上部中央へ */
        this.cx = CONFIG.WIDTH / 2;
        this.cy = -this.core.height / 2;
        this.targetCy = cfg.coreY + this.core.height / 2;
        this.placeCore();
    },

    placeCore: function () {
        this.core.x = this.cx - this.core.width / 2;
        this.core.y = this.cy - this.core.height / 2;
    },

    /* パーツ i の静止位置 / 合体位置 / 画面外の出現位置 */
    ringPos: function (i) {
        var d = MIDBOSS_DIRS[i], r = this.cfg.ringR;
        return [this.cx + d[0] * r, this.cy + d[1] * r];
    },
    attachPos: function (i) {
        var d = MIDBOSS_DIRS[i], r = this.cfg.attachR;
        return [this.cx + d[0] * r, this.cy + d[1] * r];
    },
    startPos: function (i) {
        var d = MIDBOSS_DIRS[i], ring = this.ringPos(i);
        var pw = this.parts[i].width, ph = this.parts[i].height;
        if (d[1] < 0) { return [ring[0], -ph]; }                    /* 上の外 */
        if (d[1] > 0) { return [ring[0], CONFIG.HEIGHT + ph]; }     /* 下の外 */
        if (d[0] < 0) { return [-pw, ring[1]]; }                    /* 左の外 */
        return [CONFIG.WIDTH + pw, ring[1]];                        /* 右の外 */
    },

    /* パーツを (中心座標) へ置く */
    setPart: function (i, x, y) {
        var p = this.parts[i];
        p.x = x - p.width / 2;
        p.y = y - p.height / 2;
        p.visible = true;
    },

    /*
     * 透明度。enchant の Group は opacity を持たない(Entity のプロパティ)ため、
     * コアと各パーツに個別に設定する。
     */
    setAlpha: function (a) {
        var i;
        this.core.opacity = a;
        for (i = 0; i < 4; i++) { this.parts[i].opacity = a; }
    },

    /* コアに攻撃が通る状態か(パーツの移動開始前は効かない) */
    coreVulnerable: function () {
        return this.state === 'merge' || this.state === 'full';
    },

    /* コアの当たり判定 */
    coreTarget: function () {
        return { x: this.cx, y: this.cy, r: this.core.width * 0.36 };
    },

    /* 障害物としてのパーツ(常に無敵。飛来中だけ判定なし) */
    partTargets: function () {
        var list = [], i, p;
        if (!this.partsSolid) { return list; }
        for (i = 0; i < 4; i++) {
            p = this.parts[i];
            if (!p.visible) { continue; }
            list.push({
                idx: i,
                x: p.x + p.width / 2,
                y: p.y + p.height / 2,
                r: p.width * 0.36
            });
        }
        return list;
    },

    /* ショットがパーツに弾かれた(ダメージにはならない) */
    deflect: function (idx) {
        this.parts[idx].flash = 4;
    },

    /* 戻り値: 撃破したら 'bonus'(合体前) / 'normal'(合体後)、まだなら null */
    damage: function (n) {
        if (!this.coreVulnerable()) { return null; }
        this.hp -= n;
        this.flash = 3;
        if (this.hp > 0) {
            AudioMgr.playSe('hit');
            return null;
        }
        this.hp = 0;
        this.result = (this.state === 'merge') ? 'bonus' : 'normal';
        this.state = 'dying';
        this.t = 0;
        AudioMgr.playSe(this.result === 'bonus' ? 'fanfare' : 'boss_explosion');
        return this.result;
    },

    update: function (scene) {
        var cfg = this.cfg, t = ++this.t, i, k, a, b;

        switch (this.state) {
        case 'enter':
            this.cy += 1.6;
            if (this.cy >= this.targetCy) {
                this.cy = this.targetCy;
                this.state = 'flyin';
                this.t = 0;
                /* 画面外の出現位置を確定させておく */
                this.starts = [];
                for (i = 0; i < 4; i++) { this.starts.push(this.startPos(i)); }
            }
            this.placeCore();
            break;

        case 'flyin':
            /* 四方の画面外から静止位置へ飛び込む。この間は当たり判定なし */
            k = Math.min(1, t / cfg.flyInFrames);
            for (i = 0; i < 4; i++) {
                a = this.starts[i];
                b = this.ringPos(i);
                this.setPart(i, a[0] + (b[0] - a[0]) * k,
                                a[1] + (b[1] - a[1]) * k);
            }
            if (t >= cfg.flyInFrames) {
                this.state = 'hold';
                this.t = 0;
                this.partsSolid = true;    /* ここから障害物になる */
            }
            break;

        case 'hold':
            for (i = 0; i < 4; i++) { b = this.ringPos(i); this.setPart(i, b[0], b[1]); }
            if (t >= cfg.holdFrames) { this.state = 'merge'; this.t = 0; }
            break;

        case 'merge':
            k = Math.min(1, t / cfg.mergeFrames);
            for (i = 0; i < 4; i++) {
                a = this.ringPos(i);
                b = this.attachPos(i);
                this.setPart(i, a[0] + (b[0] - a[0]) * k,
                                a[1] + (b[1] - a[1]) * k);
            }
            if (t >= cfg.mergeFrames) {
                /* 合体成立。HPを合体後の値に戻して通常戦闘へ */
                this.state = 'full';
                this.t = 0;
                this.hp = cfg.hpFull;
                this.shootTimer = 30;
            }
            break;

        case 'full':
            this.cx = CONFIG.WIDTH / 2 + Math.sin(t * 0.025) * 90;
            this.cy = this.targetCy + Math.sin(t * 0.017) * 14;
            this.placeCore();
            for (i = 0; i < 4; i++) { b = this.attachPos(i); this.setPart(i, b[0], b[1]); }
            if (--this.shootTimer <= 0) {
                this.shootTimer = cfg.shootEvery;
                fireAimed(scene, this.cx, this.cy + 20, 3, 0.26, 3.0);
            }
            if (t >= cfg.fullTimeout) {       /* 倒せないままなら去る(進行不能の防止) */
                this.result = 'escaped';
                this.state = 'dying';
                this.t = 0;
            }
            break;

        case 'dying':
            this.partsSolid = false;
            if (this.result === 'escaped') {
                this.cy -= 3;                 /* 上へ退場 */
                this.placeCore();
                for (i = 0; i < 4; i++) { b = this.attachPos(i); this.setPart(i, b[0], b[1]); }
                if (this.cy < -this.core.height) { return false; }
            } else {
                if (t % 7 === 0) {
                    scene.addEffect(new Explosion(
                        this.cx + rand(-40, 40), this.cy + rand(-40, 40)));
                    /* ボーナス時はファンファーレを爆発音で潰さない */
                    if (this.result !== 'bonus') { AudioMgr.playSe('explosion'); }
                }
                if (t >= 80) { return false; }
            }
            break;
        }

        /* 見た目: 撃破中はフェード、被弾直後は点滅、静止中(コア無敵)は薄く点滅 */
        if (this.state === 'dying' && this.result !== 'escaped') {
            this.setAlpha(Math.max(0, 1 - this.t / 80));
        } else if (this.flash > 0) {
            this.flash--;
            this.setAlpha(0.45);
        } else if (this.state === 'hold') {
            this.setAlpha((this.t % 10 < 5) ? 0.6 : 1);   // コアはまだ攻撃が効かない
        } else {
            this.setAlpha(1);
        }
        /* パーツが弾いたときの点滅は個別に */
        for (i = 0; i < 4; i++) {
            if (this.parts[i].flash > 0) {
                this.parts[i].flash--;
                this.parts[i].opacity = 0.5;
            }
        }
        return true;
    }
});

/* ---------- 爆発 ---------- */

var Explosion = Class.create(Sprite, {
    initialize: function (cx, cy) {
        Sprite.call(this, ASSETS.img.explosion.fw, ASSETS.img.explosion.fh);
        this.image = imgAsset('explosion');
        this.x = cx - this.width / 2;
        this.y = cy - this.height / 2;
        this.frame = 0;
        this.t = 0;
    },
    update: function () {
        this.t++;
        this.frame = Math.min(3, Math.floor(this.t / 5));
        return this.t < 20;
    }
});

/* ---------- パワーアップアイテム ---------- */

var PowerUp = Class.create(Sprite, {
    initialize: function (cx, cy) {
        Sprite.call(this, ASSETS.img.powerup.fw, ASSETS.img.powerup.fh);
        this.image = imgAsset('powerup');
        this.frame = flickFrames(6);
        this.baseX = cx;
        this.x = cx - this.width / 2;
        this.y = cy - this.height / 2;
        this.r = 12;   // 取りやすく大きめ
        this.t = 0;
    },
    cx: function () { return this.x + this.width / 2; },
    cy: function () { return this.y + this.height / 2; },
    update: function () {
        this.t++;
        this.y += 1.3;
        this.x = this.baseX - this.width / 2 + Math.sin(this.t * 0.05) * 16;
        return this.y < CONFIG.HEIGHT + 24;
    }
});
