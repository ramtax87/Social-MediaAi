# Media preparation

Keep source files untouched. Save derived files to the private workspace with stable names tied to the source hash and intended format. Inspect each source and result; selecting an enhancement filter is not evidence that the result improved.

## Photos

Use the image editing capability available in the agent's host, including its imagegen skill/tool when provided. Inspect the original first and pass it as an actual image reference. A conservative starting instruction is:

> Clean up noise and compression artifacts, correct the exposure and white balance subtly, and improve clarity naturally. Preserve the real subject, facial identity, skin texture, body shape, product details, text, logos, and scene geometry. Do not add objects or invent detail. Keep the original composition unless a crop was requested. Return a separate image.

Only apply changes useful for that image. Do not remove watermarks, modify product labels, reshape people, or replace backgrounds under a generic “cleanup” preference. Those are separate edits to discuss when relevant. Preserve transparency when present unless the output format requires a user-chosen background.

For publishing, verify the actual output format, pixel dimensions, orientation, color appearance, file size, and lack of unwanted location metadata. Generative editors can distort text and faces: compare before/after and reject a damaged result. Resize or convert using the host's supported export path. No photo editor is bundled in this repository; if the host has none, state that and let the user choose a supported editor or original-media workflow.

## Videos

`scripts/video.py` uses local FFmpeg and FFprobe. Run `--help` for available options. It exports a separate MP4 with H.264 video, compatible pixel format, optional AAC audio, fast-start metadata, and stripped source metadata. The conservative conversion preserves content; optional denoise/audio cleanup is a separate choice. No generative video restoration, captions, music licensing, or automatic highlight selection is supplied by this helper.

From the installed skill directory:

```sh
python3 scripts/video.py inspect /absolute/path/to/source.mov
python3 scripts/video.py prepare /absolute/path/to/source.mov /absolute/workspace/prepared/clip.mp4 --dry-run
python3 scripts/video.py prepare /absolute/path/to/source.mov /absolute/workspace/prepared/clip.mp4
```

Use `--preset square|portrait|vertical|landscape` for a fitted and padded canvas, or keep the default `original` dimensions (rounded to even pixels). Optional `--denoise`, `--audio-denoise`, and `--normalize-audio` apply only when selected. Existing outputs are never overwritten. HDR sources are rejected because this helper does not perform reviewed tone mapping. Install FFmpeg through the user's normal package manager if needed; review the [official filters documentation](https://ffmpeg.org/ffmpeg-filters.html) for more specialized processing.

Inspect duration, streams, frame dimensions, rotation, and audio first. Match the selected destination's current requirements; don't assume one vertical export works for every platform. Fit/pad preserves the whole frame; approve any crop that removes meaningful content. Avoid enlarging a low-resolution source just to meet a nominal preset unless the destination requires it.

For a long video, ask about full-length publication versus a short excerpt. If the user authorizes trimming, select timestamps based on the actual contents and check the beginning/end for cut-off speech. Use a suitable editor for stabilization, subtitles, or substantial grading rather than promising these from a basic transcode. Do not add music without the user's chosen rights-cleared source.

Inspect frames near the beginning, middle, and end of each export, play representative audio, and compare duration. Check for clipped highlights, excessive sharpening, noise reduction smearing, rotated frames, black-frame errors, clipped speech, and audio drift. Keep the original if cleanup makes it worse. Only put the final checked derivative into the posting queue.

For a still photo aimed at a video-only destination, skip that destination by default. Create a slideshow or motion video only if the user requests that conversion; do not silently upload a JPEG as a video.
