/*
 * measure_midboss.js — 中ボスの「合体までの猶予」に何発コアへ当てられるかを実測する。
 *
 * パーツは常に無敵の障害物で、特に下側のパーツがコアの中央を遮るため、
 * 必要弾数(CONFIG.MIDBOSS.hpMerge)を机上で決めるのは難しい。
 * そこで「最適な位置に置いた自機が撃ちっぱなしにした場合の最大命中数」を
 * パワー別・横位置別に測り、その値を基準に hpMerge を決める。
 *
 * 使い方: index.html?debug=1 を開き、開発者コンソールで
 *     console.table(measureMidBoss())
 * 結果の maxHits が「そのパワーで理論上当てられる上限」。
 *
 * 実装メモ:
 *   requestAnimationFrame はタブが非表示だと止まるので、
 *   シーンの enterframe を手動で dispatch してフレームを進める(同期・高速)。
 *   測定中は damage() を差し替えて中ボスが死なないようにし、命中数だけ数える。
 */
function measureMidBoss(opts) {
    opts = opts || {};
    var powers = opts.powers || [1, 2, 3];
    var offsets = opts.offsets || [0, 8, 16, 24, 32, 40];
    var playerY = opts.playerY || 300;
    var maxFrames = opts.maxFrames || 600;

    var origDamage = MidBoss.prototype.damage;
    var count = { merge: 0, full: 0 };
    MidBoss.prototype.damage = function () {
        if (this.state === 'merge') { count.merge++; }
        else if (this.state === 'full') { count.full++; }
        return null;                 /* 死なせない */
    };

    function step() {
        game.currentScene.dispatchEvent(new enchant.Event('enterframe'));
    }

    function oneRun(power, dx) {
        GameState.lives = 3;
        GameState.power = power;
        GameState.score = 0;
        __dbg.stage(0);
        var sc = game.currentScene;
        /*
         * 無敵にはしない。パーツに接触して死ぬ位置は「実際には取れない位置」なので、
         * 死んだ時点で命中が止まるのが正しいモデルになる。
         * (無敵にすると、合体してくる下パーツの内側に居座れて非現実的な数が出る)
         */
        sc.player.invincible = 0;
        sc.debug.startMidBoss();
        count.merge = 0;
        count.full = 0;
        game.input.a = true;

        var f, mb, reachedFull = false;
        for (f = 0; f < maxFrames; f++) {
            mb = game.currentScene.midBoss;
            if (mb) {
                /* 最適位置に固定して撃ちっぱなし。
                   合体開始前から撃つのが最適(弾の飛行時間があるため) */
                var pl = game.currentScene.player;
                pl.x = mb.cx + dx - pl.width / 2;
                pl.y = playerY;
                if (mb.state === 'full' && mb.t > 2) { reachedFull = true; break; }
                if (!pl.alive) { break; }        /* 死んだらそこまで */
            }
            step();
        }
        game.input.a = false;
        return { power: power, dx: dx, mergeHits: count.merge, ok: reachedFull,
                 died: !game.currentScene.player.alive };
    }

    var results = [];
    powers.forEach(function (power) {
        offsets.forEach(function (dx) {
            [1, -1].forEach(function (sign) {
                if (dx === 0 && sign === -1) { return; }
                results.push(oneRun(power, dx * sign));
            });
        });
    });

    MidBoss.prototype.damage = origDamage;
    window.__mbMeasureDetail = results;

    return powers.map(function (p) {
        var rs = results.filter(function (r) { return r.power === p; });
        var best = rs.reduce(function (a, b) { return b.mergeHits > a.mergeHits ? b : a; });
        return { power: p, maxHits: best.mergeHits, bestOffset: best.dx,
                 diedCount: rs.filter(function (r) { return r.died; }).length,
                 runs: rs.length };
    });
}
