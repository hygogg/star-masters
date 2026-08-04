/*
 * sound.h — BGM / SE
 *
 * WAVのままではDSのメインRAM(4MB)に収まらないため、
 * BGMは MOD モジュール(tools/generate_nds_audio.py が生成)にして
 * maxmod で鳴らす。SEは 11025Hz 8bit の WAV。
 * 実体のファイルは audio/ にあり、ビルド時に mmutil が
 * soundbank へまとめる。
 */
#ifndef SOUND_H
#define SOUND_H

#include <nds.h>

typedef enum {
    BGM_TITLE = 0,
    BGM_STAGE1,
    BGM_STAGE2,
    BGM_STAGE3,
    BGM_MIDBOSS,
    BGM_BOSS,
    BGM_ENDING,
    BGM_COUNT
} BgmId;

typedef enum {
    SE_SHOT = 0,
    SE_HIT,
    SE_EXPLOSION,
    SE_PLAYER_DEATH,
    SE_POWERUP,
    SE_BOSS_EXPLOSION,
    SE_START,
    SE_CLEAR,
    SE_FANFARE,
    SE_COUNT
} SeId;

void snd_init(void);
void snd_bgm(int id);          /* 同じ曲なら鳴らし直さない */
void snd_bgm_stop(void);
void snd_se(int id);
bool snd_toggle_mute(void);    /* 戻り値: ミュート中か */

#endif /* SOUND_H */
