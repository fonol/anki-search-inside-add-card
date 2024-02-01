#!/usr/bin/fish

zip -r addon-packed.zip . \
	-x ".gitignore" \
    -x "*.zip" \
    -x "__pycache__/*" \
    -x "./*/__pycache__/*" \
    -x "web/node_modules/*" \
    -x "web/src/*" \
    -x "index" \
    -x "*.bat" \
    -x "*.fish" \
    -x "*.txt" \
    -x "*.sh" \
    -x "*.db" \
    -x "./*/*.db" \
    -x "meta.json" \
    -x ".vscode" \
    -x "tests/*" \
    -x "src/rs/siacrs/siacrs_venv/*" \
    -x "src/rs/siacrs/src/*" \
    -x "src/rs/siacrs/target/*" \
    -x "web/package.json" \
    -x "web/package-lock.json" \
    -x "web/webpack.config.js" \
    -x ".git/*" \
    -x ".github/*" \
	-x "venv/*"

