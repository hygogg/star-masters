/*
 * sound.c — maxmod のラッパ
 *
 * mmutil が生成するシンボル名(MOD_*, SFX_*)への依存はこのファイルの
 * 変換表だけに閉じてある。音源ファイル名を変えたらここを直す。
 */
#include <maxmod9.h>
#include "sound.h"
#include "soundbank.h"
#include "soundbank_bin.h"

static const int bgm_mod[BGM_COUNT] = {
    MOD_TITLE, MOD_STAGE1, MOD_STAGE2, MOD_STAGE3, MOD_MIDBOSS, MOD_BOSS, MOD_ENDING
};

static const int se_sfx[SE_COUNT] = {
    SFX_SHOT, SFX_HIT, SFX_EXPLOSION, SFX_PLAYER_DEATH,
    SFX_POWERUP, SFX_BOSS_EXPLOSION, SFX_START, SFX_CLEAR, SFX_FANFARE
};

#define VOL_BGM 700    /* 0..1024 */
#define VOL_SE  900

static int  currentBgm = -1;
static bool muted = false;

void snd_init(void)
{
    int i;
    mmInitDefaultMem((mm_addr)soundbank_bin);

    for (i = 0; i < BGM_COUNT; i++) mmLoad(bgm_mod[i]);
    for (i = 0; i < SE_COUNT; i++)  mmLoadEffect(se_sfx[i]);

    mmSetModuleVolume(VOL_BGM);
    mmSetEffectsVolume(VOL_SE);
}

void snd_bgm(int id)
{
    if (id < 0 || id >= BGM_COUNT) return;
    if (currentBgm == id) return;
    if (currentBgm >= 0) mmStop();
    currentBgm = id;
    mmStart(bgm_mod[id], MM_PLAY_LOOP);
}

void snd_bgm_stop(void)
{
    if (currentBgm >= 0) mmStop();
    currentBgm = -1;
}

void snd_se(int id)
{
    if (id < 0 || id >= SE_COUNT) return;
    mmEffect(se_sfx[id]);
}

bool snd_toggle_mute(void)
{
    muted = !muted;
    mmSetModuleVolume(muted ? 0 : VOL_BGM);
    mmSetEffectsVolume(muted ? 0 : VOL_SE);
    return muted;
}
