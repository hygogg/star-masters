/*
 * gfx.h — 描画レイヤ(2画面をまたぐスプライト管理・背景スクロール・文字表示)
 *
 * 画面ID: 0 = 上画面(メインエンジン), 1 = 下画面(サブエンジン)
 * 座標はすべて「プレイフィールド座標」(256x384)。
 * 上画面が y 0..191、下画面が y 192..383 を表示する。
 */
#ifndef GFX_H
#define GFX_H

#include "game.h"
/* スプライトの寸法定義と文字色(TXT_*)はここで供給される */
#include "gfx_data.h"

#define SCREEN_TOP    0
#define SCREEN_BOTTOM 1

void gfx_init(void);
/* Vブランク中に呼ぶ: OAM とスクロールレジスタへ反映 */
void gfx_commit(void);

/* ---- 背景 ---- */
void gfx_load_bg(int idx);            /* bg_data[idx] を両エンジンへ */
void gfx_set_bg_scroll(s32 fxOffset); /* プレイフィールド基準の縦スクロール量(24.8) */
void gfx_bg_visible(bool on);

/* ---- スプライト ---- */
void spr_begin(void);
/* x,y はプレイフィールド座標でのスプライト左上。画面をまたぐ場合は両方に描く */
void spr_draw(int id, int frame, int x, int y);
void spr_end(void);
int  spr_w(int id);
int  spr_h(int id);

/* ---- 文字 ---- */
#define TXT_COLS 32
#define TXT_ROWS 64            /* 256x512 のテキストBG。0..23行が1画面ぶん */

void txt_clear(int screen);
void txt_put(int screen, int col, int row, const char *s, int color);
void txt_center(int screen, int row, const char *s, int color);
void txt_num(int screen, int col, int row, u32 value, int digits, int color);
void txt_scroll(int screen, int pixels);   /* テキスト層の縦スクロール(スタッフロール用) */

#endif /* GFX_H */
