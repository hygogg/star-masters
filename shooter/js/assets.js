/*
 * assets.js — アセットマニフェスト
 *
 * 画像・SE・BGM はすべてここで一元管理する。
 * ファイルを差し替えたいときは assets/ 配下の PNG / WAV を置き換えるか、
 * ここの path を書き換えるだけでよい(ゲームコード側の変更は不要)。
 *
 * 画像の約束事:
 *   - fw / fh はスプライト1コマの幅・高さ(px)。frames はコマ数。
 *   - アニメーションするスプライトはコマを横に並べた1枚のシートにする。
 *     例: player.png は 32x32 が2コマ → 画像サイズ 64x32
 *   - ドット絵は原寸(1ドット=2px に事前拡大済み)。ゲーム内では拡縮しない。
 */
var ASSETS = {
    img: {
        player:        { path: 'assets/img/player.png',        fw: 32, fh: 32, frames: 2 },
        enemy1:        { path: 'assets/img/enemy1.png',        fw: 32, fh: 32, frames: 2 },
        enemy2:        { path: 'assets/img/enemy2.png',        fw: 32, fh: 32, frames: 2 },
        enemy3:        { path: 'assets/img/enemy3.png',        fw: 32, fh: 32, frames: 2 },
        midenemy:      { path: 'assets/img/midenemy.png',      fw: 48, fh: 48, frames: 2 },
        boss1:         { path: 'assets/img/boss1.png',         fw: 96, fh: 96, frames: 2 },
        boss2:         { path: 'assets/img/boss2.png',         fw: 96, fh: 96, frames: 2 },
        boss3:         { path: 'assets/img/boss3.png',         fw: 96, fh: 96, frames: 2 },
        bullet_player: { path: 'assets/img/bullet_player.png', fw:  8, fh: 16, frames: 1 },
        bullet_enemy:  { path: 'assets/img/bullet_enemy.png',  fw: 12, fh: 12, frames: 1 },
        explosion:     { path: 'assets/img/explosion.png',     fw: 32, fh: 32, frames: 4 },
        powerup:       { path: 'assets/img/powerup.png',       fw: 16, fh: 16, frames: 2 },
        bg1:           { path: 'assets/img/bg1.png',           fw: 320, fh: 480, frames: 1 },
        bg2:           { path: 'assets/img/bg2.png',           fw: 320, fh: 480, frames: 1 },
        bg3:           { path: 'assets/img/bg3.png',           fw: 320, fh: 480, frames: 1 }
    },
    bgm: {
        title:  'assets/bgm/title.wav',
        stage1: 'assets/bgm/stage1.wav',
        stage2: 'assets/bgm/stage2.wav',
        stage3: 'assets/bgm/stage3.wav',
        boss:   'assets/bgm/boss.wav',
        ending: 'assets/bgm/ending.wav'
    },
    se: {
        shot:           'assets/se/shot.wav',
        hit:            'assets/se/hit.wav',
        explosion:      'assets/se/explosion.wav',
        player_death:   'assets/se/player_death.wav',
        powerup:        'assets/se/powerup.wav',
        boss_explosion: 'assets/se/boss_explosion.wav',
        start:          'assets/se/start.wav',
        clear:          'assets/se/clear.wav'
    }
};

/* enchant.js の preload に渡す画像パス一覧 */
ASSETS.imagePaths = Object.keys(ASSETS.img).map(function (k) {
    return ASSETS.img[k].path;
});
