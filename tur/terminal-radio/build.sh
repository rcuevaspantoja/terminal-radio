# Recipe for Termux User Repository (TUR).
# Submit as PR: https://github.com/termux-user-repository/tur
#
# Local build (after TUR setup-environment.sh):
#   TERMUX_INSTALL_DEPS=true ./build-package.sh -a aarch64 terminal-radio
#
# On device:
#   TERMUX_NO_CLEAN=true TERMUX_INSTALL_DEPS=true ./build-package.sh -a aarch64 terminal-radio

TERMUX_PKG_HOMEPAGE=https://github.com/rcuev/terminal-radio
TERMUX_PKG_DESCRIPTION="Internet radio player for your terminal"
TERMUX_PKG_LICENSE="MIT"
TERMUX_PKG_MAINTAINER="@rcuev"
TERMUX_PKG_VERSION=0.1.0
TERMUX_PKG_SRCURL=$TERMUX_PKG_HOMEPAGE/archive/refs/tags/v${TERMUX_PKG_VERSION}.tar.gz
# Update on each release (sha256sum of the tarball).
TERMUX_PKG_SHA256=0000000000000000000000000000000000000000000000000000000000000000
TERMUX_PKG_DEPENDS="python, mpv, python-pip"
TERMUX_PKG_PLATFORM_INDEPENDENT=true
TERMUX_PKG_BUILD_IN_SRC=true

_TUR_PYPI="https://termux-user-repository.github.io/pypi/"
_EUTALIX_PYPI="https://eutalix.github.io/android-pydantic-core/"

termux_step_make_install() {
	# Runtime Python deps (wheels only for pydantic-core; built in CI, not on user device).
	pip install --no-build-isolation --prefer-binary --only-binary pydantic-core \
		--extra-index-url "$_TUR_PYPI" \
		--extra-index-url "$_EUTALIX_PYPI" \
		"httpx>=0.27.0" "pydantic>=2.3.0"
	pip install --no-build-isolation --no-deps --prefer-binary \
		--extra-index-url "$_TUR_PYPI" \
		"pydantic-settings>=2.3.0"
	pip install --no-build-isolation --prefer-binary \
		--extra-index-url "$_TUR_PYPI" \
		"textual>=0.80.0"

	local appdir="$TERMUX_PREFIX/share/terminal-radio"
	mkdir -p "$appdir"
	cp -a terminal_radio "$appdir/"
	cp pyproject.toml README.md "$appdir/" 2>/dev/null || true

	mkdir -p "$TERMUX_PREFIX/bin"
	for name in radio terminal-radio; do
		cat > "$TERMUX_PREFIX/bin/$name" <<-EOF
			#!/bin/sh
			export PYTHONPATH="$appdir:\${PYTHONPATH:-}"
			exec python -m terminal_radio "\$@"
		EOF
		chmod 755 "$TERMUX_PREFIX/bin/$name"
	done
}
