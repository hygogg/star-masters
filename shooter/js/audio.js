/*
 * audio.js — BGM / SE 再生マネージャ
 *
 * enchant.js のサウンドは環境差が大きいため、Web Audio API を直接使う。
 * fetch できない環境(file:// 直開きなど)では HTML5 Audio に自動フォールバック。
 * アセットのパスはすべて ASSETS.bgm / ASSETS.se(assets.js)から引く。
 */
var AudioMgr = (function () {
    var ctx = null;
    var buffers = {};        // name -> AudioBuffer
    var htmlCache = {};      // name -> HTMLAudioElement (フォールバック用)
    var pathOf = {};         // name -> path
    var useWebAudio = true;
    var unlocked = false;
    var muted = false;
    var bgmSource = null;    // 再生中の BGM (WebAudio)
    var bgmHtml = null;      // 再生中の BGM (HTML5)
    var currentBgm = null;
    var bgmGain = null;
    var seGain = null;
    var BGM_VOL = 0.55;
    var SE_VOL = 0.75;

    function collectPaths() {
        var k;
        for (k in ASSETS.bgm) { pathOf['bgm/' + k] = ASSETS.bgm[k]; }
        for (k in ASSETS.se)  { pathOf['se/' + k]  = ASSETS.se[k]; }
    }

    function init() {
        collectPaths();
        try {
            var AC = window.AudioContext || window.webkitAudioContext;
            ctx = new AC();
            bgmGain = ctx.createGain();
            bgmGain.gain.value = BGM_VOL;
            bgmGain.connect(ctx.destination);
            seGain = ctx.createGain();
            seGain.gain.value = SE_VOL;
            seGain.connect(ctx.destination);
        } catch (e) {
            useWebAudio = false;
        }
    }

    /* 全ファイルを読み込む。失敗しても止まらない(該当ファイルは無音になるだけ) */
    function loadAll(onComplete) {
        var names = Object.keys(pathOf);
        var remain = names.length;
        if (!useWebAudio || remain === 0) { onComplete(); return; }
        var finish = function () { if (--remain <= 0) { onComplete(); } };
        names.forEach(function (name) {
            fetch(pathOf[name]).then(function (res) {
                if (!res.ok) { throw new Error('HTTP ' + res.status); }
                return res.arrayBuffer();
            }).then(function (ab) {
                return new Promise(function (resolve, reject) {
                    ctx.decodeAudioData(ab, resolve, reject);
                });
            }).then(function (buf) {
                buffers[name] = buf;
                finish();
            }).catch(function (e) {
                console.warn('[audio] load failed: ' + pathOf[name], e);
                finish();
            });
        });
    }

    /* 初回のユーザー操作で呼ぶ(ブラウザの自動再生制限の解除) */
    function unlock() {
        if (unlocked) { return; }
        unlocked = true;
        if (ctx && ctx.state === 'suspended') { ctx.resume(); }
    }

    function htmlAudioFor(name) {
        if (!htmlCache[name]) {
            htmlCache[name] = new Audio(pathOf[name]);
        }
        return htmlCache[name];
    }

    function playSe(name) {
        if (muted || !unlocked) { return; }
        var key = 'se/' + name;
        if (useWebAudio && buffers[key]) {
            var src = ctx.createBufferSource();
            src.buffer = buffers[key];
            src.connect(seGain);
            src.start(0);
        } else if (pathOf[key]) {
            var a = htmlAudioFor(key).cloneNode();
            a.volume = SE_VOL;
            a.play().catch(function () {});
        }
    }

    function playBgm(name) {
        if (currentBgm === name) { return; }
        stopBgm();
        currentBgm = name;
        if (!unlocked) { return; }   // unlock 後に再度呼ばれる想定
        var key = 'bgm/' + name;
        if (useWebAudio && buffers[key]) {
            bgmSource = ctx.createBufferSource();
            bgmSource.buffer = buffers[key];
            bgmSource.loop = true;
            bgmSource.connect(bgmGain);
            bgmSource.start(0);
        } else if (pathOf[key]) {
            bgmHtml = htmlAudioFor(key);
            bgmHtml.loop = true;
            bgmHtml.volume = muted ? 0 : BGM_VOL;
            bgmHtml.currentTime = 0;
            bgmHtml.play().catch(function () {});
        }
    }

    /* unlock 前に指定されていた BGM を鳴らし直す */
    function resumeBgm() {
        var name = currentBgm;
        currentBgm = null;
        if (name) { playBgm(name); }
    }

    function stopBgm() {
        if (bgmSource) {
            try { bgmSource.stop(); } catch (e) {}
            bgmSource = null;
        }
        if (bgmHtml) {
            bgmHtml.pause();
            bgmHtml = null;
        }
        currentBgm = null;
    }

    function toggleMute() {
        muted = !muted;
        if (bgmGain) { bgmGain.gain.value = muted ? 0 : BGM_VOL; }
        if (seGain)  { seGain.gain.value  = muted ? 0 : SE_VOL; }
        if (bgmHtml) { bgmHtml.volume = muted ? 0 : BGM_VOL; }
        return muted;
    }

    return {
        init: init,
        loadAll: loadAll,
        unlock: unlock,
        playSe: playSe,
        playBgm: playBgm,
        resumeBgm: resumeBgm,
        stopBgm: stopBgm,
        toggleMute: toggleMute,
        isUnlocked: function () { return unlocked; }
    };
})();
