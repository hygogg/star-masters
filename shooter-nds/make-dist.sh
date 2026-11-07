#!/bin/sh
# 配布用ZIPを作る: 通常ビルドの star-masters.nds + ライセンス文 + ビルド環境の記録。
#
#   ./make-dist.sh            # バージョン名は git describe から
#   ./make-dist.sh v1.0.0     # バージョン名を指定
#
# devkitarm の `latest` は中身が入れ替わるため、ライセンス文(licenses/)を確認した
# イメージをダイジェストで固定している。別のイメージでビルドする場合は
# IMAGE=... を渡し、licenses/ の版と BUILD-INFO.txt を突き合わせて確認すること。
set -eu

cd "$(dirname "$0")"
IMAGE="${IMAGE:-devkitpro/devkitarm@sha256:116afba8df8453961de2936ffab20dd441edf4d682856c1ec8b0e53d7ed0bbf5}"
VERSION="${1:-$(git describe --tags --always --dirty 2>/dev/null || echo unknown)}"
NAME="star-masters-$VERSION"
OUT="dist/$NAME"

if ! git diff --quiet HEAD -- source include audio Makefile 2>/dev/null; then
    echo "warning: source/include/audio/Makefile に未コミットの変更がある(BUILD-INFO に dirty と記録する)" >&2
fi

# 動作確認用フラグ(TEST_* / DEMO_*)を混ぜない通常ビルド
docker run --rm -v "$PWD:/w" -w /w -u "$(id -u):$(id -g)" "$IMAGE" \
    sh -c 'make clean >/dev/null && make CFLAGS_EXTRA= >/dev/null'

PKGS=$(docker run --rm "$IMAGE" dkp-pacman -Q \
    calico default-arm7 libnds maxmod-nds devkitarm-newlib devkitarm-gcc devkitARM ndstool)
DIGEST=$(docker image inspect "$IMAGE" --format '{{index .RepoDigests 0}}' 2>/dev/null || echo "$IMAGE")

rm -rf "$OUT" "dist/$NAME.zip"
mkdir -p "$OUT"
cp star-masters.nds "$OUT/"
cp -R licenses "$OUT/licenses"
{
    echo "STAR MASTERS (Nintendo DS) build info"
    echo
    echo "version      : $VERSION"
    echo "git commit   : $(git rev-parse HEAD 2>/dev/null || echo unknown)"
    echo "built (UTC)  : $(date -u '+%Y-%m-%d %H:%M:%S')"
    echo "rom sha256   : $(shasum -a 256 star-masters.nds | cut -d' ' -f1)"
    echo "image        : $DIGEST"
    echo
    echo "packages in the build image:"
    echo "$PKGS" | sed 's/^/  /'
    echo
    echo "source code  : https://github.com/hygogg/star-masters"
} > "$OUT/BUILD-INFO.txt"

(cd dist && zip -qrX "$NAME.zip" "$NAME" -x '*.DS_Store')
echo "dist/$NAME.zip"
cat "$OUT/BUILD-INFO.txt"
