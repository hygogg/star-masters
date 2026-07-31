/*
 * main.c — STAR MASTERS (Nintendo DS)
 *
 * enchant.js 製の同名ブラウザゲームを devkitARM + libnds + maxmod で移植したもの。
 * 上下2画面を縦に連結して 256x384 の縦スクロールシューティングにしている。
 *
 * 操作:
 *   十字キー / タッチ … 移動
 *   A B X Y          … ショット(押しっぱなしで連射)
 *   START            … ポーズ
 *   SELECT           … ミュート
 */
#include <nds.h>

#include "game.h"
#include "gfx.h"
#include "sound.h"

int main(void)
{
    gfx_init();
    snd_init();
    game_init();

    while (1) {
        game_frame();          /* 更新 + 影バッファへの描画 */
        swiWaitForVBlank();
        gfx_commit();          /* Vブランク中に OAM / スクロールを反映 */
    }
    return 0;
}
