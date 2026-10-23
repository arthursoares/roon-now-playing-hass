# Integration brand images

The integration ships `icon.png` (256 × 256) and `icon@2x.png` (512 × 512)
in `custom_components/roon_now_playing/brand/`. Both are RGBA PNGs with
transparent corners. The dark rounded tile and amber musical note reproduce
the project's existing favicon. The tile fills the canvas without added padding.
Home Assistant uses the icon when a separate logo or dark variant is absent.

## Source and reuse

`favicon.svg` is an unchanged copy of
[`site/public/favicon.svg`](https://github.com/arthursoares/roon-now-playing/blob/f96918a930fccd350552a21c36b6b9802e353340/site/public/favicon.svg)
from Arthur Soares's Roon Now Playing server project at commit
`f96918a930fccd350552a21c36b6b9802e353340`.
The file was introduced by Arthur Soares in commit
`d02a81e77f2f82bf2d35002c1e6f9e335cd979e7`.
Its SHA-256 is
`1e95b903203b80c3e06fa3c5ff5abc536eb1d6f4fa9bc2e2c9377f31e2defc03`.

Arthur authorized reuse of this project artwork for this integration. The source
project has no tracked standalone license or package license declaration at that
commit; this note does not attribute an upstream license to it. The copied source
and rendered images are distributed with this integration under its existing
[MIT license](../../LICENSE), copyright (c) 2025 Arthur Soares.

## Reproduce

From the repository root, using ImageMagick 6.9.12-98 Q16:

```sh
convert -background none -density 1152 docs/branding/favicon.svg \
  -resize 512x512 -strip PNG32:custom_components/roon_now_playing/brand/icon@2x.png
convert custom_components/roon_now_playing/brand/icon@2x.png \
  -resize 256x256 -strip PNG32:custom_components/roon_now_playing/brand/icon.png
```

PNG32 explicitly preserves 8-bit RGBA. Rendering and resizing are deterministic
with that toolchain; no image generation service is involved.

## Requirements

[HACS documents the local brand directory](https://www.hacs.xyz/docs/publish/include/#check-brands)
and checks for `brand/icon.png` before consulting the external brands registry.
[Home Assistant documents](https://contributors.home-assistant.io/core/integrations/brands/)
PNG images, square 256/512-pixel icons, trimmed edges, and preferred transparency.
Local brand images are supported since Home Assistant 2026.3; older supported
versions can still run the integration but will not display these local images.
