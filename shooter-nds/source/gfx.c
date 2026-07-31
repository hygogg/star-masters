/*
 * gfx.c — 描画レイヤ
 *
 * DSの2Dエンジンは1画面につき1つ(メイン=上画面 / サブ=下画面)。
 * VRAMもOAMもエンジンごとに独立しているので、
 *   - スプライトの絵は両エンジンのVRAMに二重に置く
 *   - 画面の境界をまたぐオブジェクトは両エンジンのOAMに登録する
 * という作りにしてある。
 *
 * BG構成(両エンジン共通):
 *   BG3 … ステージ背景。8bpp テキストBG 256x256、縦スクロール(wrap)
 *   BG0 … 文字。4bpp テキストBG 256x512(スタッフロールで縦に長く使う)
 *   優先度: BG0(0) < スプライト(2) < BG3(3)   ※数値が小さいほど手前
 *
 * 文字色: フォントのドットはすべてパレット値1。
 *   4bppBGのパレットバンク(bits12-15)を切り替えて色を変える。
 *   背景(8bpp)がBGパレット0..127しか使わないことを前提に、
 *   バンク8..15(=BGパレット128..255)を文字色に割り当てている。
 *   → gfx_load_bg() で実際の使用インデックスを検査している。
 */
#include <string.h>
#include "gfx.h"
#include "gfx_data.h"

/* ---------- スプライト定義表 (SprId と順序を一致させる) ---------- */
typedef struct {
    const u8   *data;
    int         w, h, frames, tiles;
    SpriteSize  size;
} SprDef;

#define DEF(ID, lower, UPPER) \
    [ID] = { spr_##lower, SPR_##UPPER##_W, SPR_##UPPER##_H, \
             SPR_##UPPER##_FRAMES, SPR_##UPPER##_TILES, SPR_##UPPER##_SIZE }

static const SprDef spr_defs[SPR_COUNT] = {
    DEF(SPR_PLAYER,    player,        PLAYER),
    DEF(SPR_ENEMY1,    enemy1,        ENEMY1),
    DEF(SPR_ENEMY2,    enemy2,        ENEMY2),
    DEF(SPR_ENEMY3,    enemy3,        ENEMY3),
    DEF(SPR_MIDENEMY,  midenemy,      MIDENEMY),
    DEF(SPR_BOSS1,     boss1,         BOSS1),
    DEF(SPR_BOSS2,     boss2,         BOSS2),
    DEF(SPR_BOSS3,     boss3,         BOSS3),
    DEF(SPR_BULLET_P,  bullet_player, BULLET_PLAYER),
    DEF(SPR_BULLET_E,  bullet_enemy,  BULLET_ENEMY),
    DEF(SPR_EXPLOSION, explosion,     EXPLOSION),
    DEF(SPR_POWERUP,   powerup,       POWERUP),
};

#define MAX_FRAMES 4
static u16 *gfxTop[SPR_COUNT][MAX_FRAMES];
static u16 *gfxBot[SPR_COUNT][MAX_FRAMES];

/* ---------- BG ハンドル ---------- */
static int bgTopScene, bgBotScene;    /* BG3: ステージ背景 */
static int bgTopText,  bgBotText;     /* BG0: 文字 */
static u16 *mapTopText, *mapBotText;
static s32 textScrollPx[2] = { 0, 0 };

/* ---------- OAM 使用数 ---------- */
static int oamCountTop, oamCountBot;

/* 文字色パレットバンク(BGパレット 128..255 を使う) */
#define TXT_BANK_BASE 8

/* ============================================================ */
/* 初期化                                                        */
/* ============================================================ */

static void upload_sprites(void)
{
    int i, f;
    for (i = 0; i < SPR_COUNT; i++) {
        const SprDef *d = &spr_defs[i];
        u32 frameBytes = (u32)d->tiles * 64;
        for (f = 0; f < d->frames; f++) {
            u16 *pt = oamAllocateGfx(&oamMain, d->size, SpriteColorFormat_256Color);
            u16 *pb = oamAllocateGfx(&oamSub,  d->size, SpriteColorFormat_256Color);
            dmaCopy(d->data + frameBytes * f, pt, frameBytes);
            dmaCopy(d->data + frameBytes * f, pb, frameBytes);
            gfxTop[i][f] = pt;
            gfxBot[i][f] = pb;
        }
        /* 未使用のコマは0コマ目を指しておく(安全のため) */
        for (; f < MAX_FRAMES; f++) {
            gfxTop[i][f] = gfxTop[i][0];
            gfxBot[i][f] = gfxBot[i][0];
        }
    }
}

static void upload_font(void)
{
    int b;
    u32 bytes = (u32)FONT_CHARS * 32;          /* 4bpp: 1タイル32byte */

    dmaCopy(font_tiles, bgGetGfxPtr(bgTopText), bytes);
    dmaCopy(font_tiles, bgGetGfxPtr(bgBotText), bytes);

    /* バンク b のインデックス1 に色を入れる → map の bits12-15 で色を選べる */
    for (b = 0; b < 8; b++) {
        int bank = TXT_BANK_BASE + b;
        BG_PALETTE[bank * 16 + 1]     = font_pal[b];
        BG_PALETTE_SUB[bank * 16 + 1] = font_pal[b];
    }
}

void gfx_init(void)
{
    powerOn(POWER_ALL_2D);
    lcdMainOnTop();

    vramSetPrimaryBanks(VRAM_A_MAIN_BG, VRAM_B_MAIN_SPRITE,
                        VRAM_C_SUB_BG,  VRAM_D_SUB_SPRITE);

    videoSetMode(MODE_0_2D | DISPLAY_BG0_ACTIVE | DISPLAY_BG3_ACTIVE |
                 DISPLAY_SPR_ACTIVE | DISPLAY_SPR_1D);
    videoSetModeSub(MODE_0_2D | DISPLAY_BG0_ACTIVE | DISPLAY_BG3_ACTIVE |
                    DISPLAY_SPR_ACTIVE | DISPLAY_SPR_1D);

    /* mapBase は2KB単位, tileBase は16KB単位。
       BG3マップ: slot0(0..2KB) / 文字マップ: slot1-2(2..6KB)
       BG3タイル: 16KB.. / フォントタイル: 96KB..                         */
    bgTopScene = bgInit(3, BgType_Text8bpp, BgSize_T_256x256, 0, 1);
    bgBotScene = bgInitSub(3, BgType_Text8bpp, BgSize_T_256x256, 0, 1);
    bgTopText  = bgInit(0, BgType_Text4bpp, BgSize_T_256x512, 1, 6);
    bgBotText  = bgInitSub(0, BgType_Text4bpp, BgSize_T_256x512, 1, 6);

    bgSetPriority(bgTopScene, 3);
    bgSetPriority(bgBotScene, 3);
    bgSetPriority(bgTopText, 0);
    bgSetPriority(bgBotText, 0);

    mapTopText = bgGetMapPtr(bgTopText);
    mapBotText = bgGetMapPtr(bgBotText);

    oamInit(&oamMain, SpriteMapping_1D_64, false);
    oamInit(&oamSub,  SpriteMapping_1D_64, false);

    upload_sprites();
    upload_font();

    dmaCopy(spr_pal, SPRITE_PALETTE,     512);
    dmaCopy(spr_pal, SPRITE_PALETTE_SUB, 512);

    txt_clear(SCREEN_TOP);
    txt_clear(SCREEN_BOTTOM);
    bgUpdate();
}

/* ============================================================ */
/* 背景                                                          */
/* ============================================================ */

void gfx_load_bg(int idx)
{
    const BgData *b = &bg_data[idx];

    dmaCopy(b->tiles, bgGetGfxPtr(bgTopScene), b->tiles_len);
    dmaCopy(b->tiles, bgGetGfxPtr(bgBotScene), b->tiles_len);
    dmaCopy(b->map,   bgGetMapPtr(bgTopScene), 32 * 32 * 2);
    dmaCopy(b->map,   bgGetMapPtr(bgBotScene), 32 * 32 * 2);

    /* 背景は8bppでBGパレット全域を使いうるが、文字色にバンク8..15
       (=128..255)を使っているため、先頭128色ぶんだけ転送する。
       generate_nds_gfx.py 側で背景の色数<=128を保証している。        */
    dmaCopy(b->pal, BG_PALETTE,     128 * 2);
    dmaCopy(b->pal, BG_PALETTE_SUB, 128 * 2);
}

void gfx_set_bg_scroll(s32 fxOffset)
{
    /* プレイフィールドが下へ流れる = ビュー原点を上へ動かす。
       背景タイルマップは256pxで巡回するので mod 256 でよい。
       下画面は上画面の192px下の領域を映す。                       */
    int y = FX2I(fxOffset);
    int top = ((-y) % 256 + 256) % 256;
    int bot = ((-y + SCR_H) % 256 + 256) % 256;
    bgSetScroll(bgTopScene, 0, top);
    bgSetScroll(bgBotScene, 0, bot);
}

void gfx_bg_visible(bool on)
{
    if (on) {
        bgShow(bgTopScene);
        bgShow(bgBotScene);
    } else {
        bgHide(bgTopScene);
        bgHide(bgBotScene);
    }
}

/* ============================================================ */
/* スプライト                                                    */
/* ============================================================ */

void spr_begin(void)
{
    oamCountTop = 0;
    oamCountBot = 0;
}

void spr_draw(int id, int frame, int x, int y)
{
    const SprDef *d = &spr_defs[id];

    if (frame >= d->frames) frame = d->frames - 1;
    if (frame < 0) frame = 0;

    /* 横方向で完全に外れているものは両画面ぶん省く */
    if (x + d->w <= 0 || x >= SCR_W) return;

    /* 上画面: プレイフィールド y 0..191 */
    if (y + d->h > 0 && y < SCR_H && oamCountTop < OAM_LIMIT) {
        oamSet(&oamMain, oamCountTop++, x, y, 2, 0,
               d->size, SpriteColorFormat_256Color, gfxTop[id][frame],
               -1, false, false, false, false, false);
    }
    /* 下画面: プレイフィールド y 192..383 */
    {
        int sy = y - SCR_H;
        if (sy + d->h > 0 && sy < SCR_H && oamCountBot < OAM_LIMIT) {
            oamSet(&oamSub, oamCountBot++, x, sy, 2, 0,
                   d->size, SpriteColorFormat_256Color, gfxBot[id][frame],
                   -1, false, false, false, false, false);
        }
    }
}

int spr_w(int id) { return spr_defs[id].w; }
int spr_h(int id) { return spr_defs[id].h; }

void spr_end(void)
{
    int i;
    for (i = oamCountTop; i < OAM_LIMIT; i++) oamSetHidden(&oamMain, i, true);
    for (i = oamCountBot; i < OAM_LIMIT; i++) oamSetHidden(&oamSub,  i, true);
}

/* oamSet / bgSetScroll はいずれもメインRAM上の影バッファを書くだけなので、
   実際のOAM・スクロールレジスタへの反映はVブランク中にここで行う。
   (表示中に転送するとスプライトがちらつく)                            */
void gfx_commit(void)
{
    oamUpdate(&oamMain);
    oamUpdate(&oamSub);
    bgUpdate();
}

/* ============================================================ */
/* 文字                                                          */
/* ============================================================ */

/* 256x512 のテキストBGは 32x32 のブロック2枚で構成される。
   32行目以降は別ブロック(+1024エントリ)にある。 */
static inline int map_idx(int row, int col)
{
    if (row < 32) return row * 32 + col;
    return 1024 + (row - 32) * 32 + col;
}

static inline u16 *text_map(int screen)
{
    return (screen == SCREEN_TOP) ? mapTopText : mapBotText;
}

void txt_clear(int screen)
{
    u16 *m = text_map(screen);
    /* 空白(ASCII 32)のタイルは全透明なのでそれで埋める */
    int i;
    u16 blank = (u16)(' ' - FONT_FIRST_CHAR);
    for (i = 0; i < 32 * 64; i++) m[i] = blank;
    textScrollPx[screen] = 0;
    bgSetScroll((screen == SCREEN_TOP) ? bgTopText : bgBotText, 0, 0);
}

void txt_put(int screen, int col, int row, const char *s, int color)
{
    u16 *m = text_map(screen);
    u16 bank = (u16)((TXT_BANK_BASE + (color & 7)) << 12);

    if (row < 0 || row >= TXT_ROWS) return;
    for (; *s; s++, col++) {
        unsigned char c = (unsigned char)*s;
        if (col < 0 || col >= TXT_COLS) continue;
        if (c >= 'a' && c <= 'z') c -= 32;            /* 大文字フォントのみ */
        if (c < FONT_FIRST_CHAR || c >= FONT_FIRST_CHAR + FONT_CHARS)
            c = ' ';
        m[map_idx(row, col)] = (u16)(c - FONT_FIRST_CHAR) | bank;
    }
}

void txt_center(int screen, int row, const char *s, int color)
{
    int len = (int)strlen(s);
    int col = (TXT_COLS - len) / 2;
    if (col < 0) col = 0;
    txt_put(screen, col, row, s, color);
}

void txt_num(int screen, int col, int row, u32 value, int digits, int color)
{
    char buf[12];
    int i;
    if (digits > 10) digits = 10;
    buf[digits] = 0;
    for (i = digits - 1; i >= 0; i--) {
        buf[i] = (char)('0' + (value % 10));
        value /= 10;
    }
    txt_put(screen, col, row, buf, color);
}

void txt_scroll(int screen, int pixels)
{
    textScrollPx[screen] = pixels;
    bgSetScroll((screen == SCREEN_TOP) ? bgTopText : bgBotText, 0, pixels);
}
