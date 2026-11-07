/*
 * main.js — 起動処理
 *
 * enchant() 自体は index.html(lib 読み込み直後)で呼び出し済み。
 * ここでは Core の初期化、キー割り当て、画像プリロード、音声アンロック、
 * ポーズ/ミュート、デバッグ用ショートカット(?debug=1 のときだけ有効)を行う。
 *
 * 注意: enchant.js は PREVENT_DEFAULT_KEY_CODES のキーに対して capture 段階で
 * stopPropagation() するため、document に付けるリスナーはすべて capture: true にする。
 */

/* Space キーでページがスクロールしないように(デフォルトは矢印キーのみ抑制) */
enchant.ENV.PREVENT_DEFAULT_KEY_CODES.push(32);

var game = null;

window.onload = function () {
    GameState.loadHiScore();
    AudioMgr.init();

    game = new Core(CONFIG.WIDTH, CONFIG.HEIGHT);
    game.fps = CONFIG.FPS;

    /*
     * 高リフレッシュレート対策。
     * enchant 0.8.3 は fps>=60 のとき requestAnimationFrame に直結するため、
     * 120Hz ディスプレイ(ProMotion 等)では 120fps で進行し全てが2倍速になる。
     * tick を時間ベースで間引いて CONFIG.FPS に固定する。
     */
    (function () {
        var interval = 1000 / CONFIG.FPS;
        var next = window.getTime();
        var origTick = game._tick;
        game._tick = function (time) {
            var now = window.getTime();
            if (now < next - 1) {              // まだ早い: 次の vsync を待つ
                this._requestNextFrame(0);
                return;
            }
            if (now - next > interval * 4) {   // タブ非表示明け等の追い上げ防止
                next = now;
            }
            next += interval;
            origTick.call(this, time);
        };
    })();

    /*
     * キー割り当て。enchant は同じボタン名に複数キーを割り当てると
     * 片方のキーを離しただけで押下状態が消えるため、キーごとに別名を振り、
     * 判定側(entities.js の inputShot / Player.update)で OR を取る。
     */
    game.keybind(90, 'a');      // Z         → ショット
    game.keybind(32, 'b');      // Space     → ショット
    game.keybind(88, 'c');      // X         → ショット(予備)
    game.keybind(87, 'up2');    // W
    game.keybind(65, 'left2');  // A
    game.keybind(83, 'down2');  // S
    game.keybind(68, 'right2'); // D

    game.preload(ASSETS.imagePaths);

    game.onload = function () {
        AudioMgr.loadAll(function () {
            game.replaceScene(makeTitleScene());
        });
    };
    game.start();

    /* 最初のユーザー操作で音声を解禁(ブラウザの自動再生制限対応) */
    var unlockHandler = function () {
        if (AudioMgr.isUnlocked()) { return; }
        AudioMgr.unlock();
        AudioMgr.resumeBgm();
        var s = game.currentScene;
        if (s && s.onUnlock) { s.onUnlock(); }
    };
    document.addEventListener('keydown', unlockHandler, true);
    document.addEventListener('mousedown', unlockHandler, true);
    document.addEventListener('touchstart', unlockHandler,
                              { capture: true, passive: true });

    /* P: ポーズ / M: ミュート(ポーズ中でも効くよう document で拾う) */
    document.addEventListener('keydown', function (ev) {
        var cs = game.currentScene;
        /* デモ中は任意のキーでタイトルへ(P のポーズはこの押下では発動させない) */
        if (cs && cs.demo && cs.demoExit) {
            if (!ev.ctrlKey && !ev.metaKey && !ev.altKey) { cs.demoExit(); }
            return;
        }
        if (cs && cs.onAnyInput) { cs.onAnyInput(); }   // タイトルのアイドルリセット
        if (ev.keyCode === 80) {           // P
            var s = game.currentScene;
            if (s && typeof s.paused === 'boolean') {
                s.paused = !s.paused;
                if (s.pauseMsg) { s.pauseMsg.visible = s.paused; }
            }
        } else if (ev.keyCode === 77) {    // M
            AudioMgr.toggleMute();
        }
    }, true);

    /* ウィンドウリサイズでタッチ座標の基準がずれるのを補正
       (enchant は起動時に一度しかステージ位置を測らない) */
    window.addEventListener('resize', function () {
        if (!game || !game._element) { return; }
        var b = game._element.getBoundingClientRect();
        game._pageX = Math.round(b.left + (window.scrollX || 0));
        game._pageY = Math.round(b.top + (window.scrollY || 0));
    });

    /* ---------- デバッグモード(index.html?debug=1) ---------- */
    if (/[?&]debug=1/.test(location.search)) {
        window.__dbg = {
            /* n = 0..2 のステージへ即ジャンプ */
            stage: function (n) {
                DemoMgr.end();
                if (GameState.lives <= 0) { GameState.reset(); }
                AudioMgr.stopBgm();
                game.replaceScene(makeStageScene(n));
            },
            /* 中ボス演出を即開始 */
            midboss: function () {
                var s = game.currentScene;
                if (s && s.debug) { s.debug.startMidBoss(); }
            },
            /* 現ステージのボス戦へスキップ */
            boss: function () {
                var s = game.currentScene;
                if (s && s.debug) { s.debug.skipToBoss(); }
            },
            /* ボスを即撃破 */
            kill: function () {
                var s = game.currentScene;
                if (s && s.debug) { s.debug.killBoss(); }
            },
            /* デモプレイを即開始 */
            demo: function () { startDemo(); },
            /* 無敵化 */
            god: function () {
                var s = game.currentScene;
                if (s && s.player) { s.player.invincible = 9999999; }
            }
        };
        document.addEventListener('keydown', function (ev) {
            if (ev.keyCode >= 49 && ev.keyCode <= 51) { window.__dbg.stage(ev.keyCode - 49); } // 1-3
            if (ev.keyCode === 78) { window.__dbg.midboss(); } // N
            if (ev.keyCode === 66) { window.__dbg.boss(); }  // B
            if (ev.keyCode === 75) { window.__dbg.kill(); }  // K
            if (ev.keyCode === 71) { window.__dbg.god(); }   // G
        }, true);
        console.log('[debug] 1/2/3: stage jump, N: mid-boss, B: skip to boss, K: kill boss, G: god mode');
    }
};
