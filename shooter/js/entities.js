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
