# Resolution Selector Plus - Custom node for ComfyUI

Custom node for [ComfyUI](https://github.com/comfyanonymous/ComfyUI) providing easy resolution and empty latent selection for image generation workflows.

![Resolution Selector Plus v2 node](node_preview.png)

## Features

- **Resolution Selector Plus v2:** pick aspect ratio and megapixels, then choose from matching resolutions.
- **Up to four resolution slots:** each active slot has width, height, and empty latent outputs.
- **Per-slot model and rounding multiple:** choose a model family and pixel multiple independently for each slot.
- **Legacy Resolution Selector Plus:** existing model presets and custom dimensions remain available for saved workflows.

## Installation

### ComfyUI Manager (recommended)

In ComfyUI, open **Manager > Custom Nodes Manager**, search for **ComfyUI_ResolutionSelectorPlus**, click **Install**, then restart ComfyUI.

### Manual install

```bash
# Change to the directory you installed ComfyUI
cd pathTo/ComfyUI

# Change to the custom_nodes directory
cd custom_nodes

# Clone the repo into custom_nodes
git clone https://github.com/bradsec/ComfyUI_ResolutionSelectorPlus.git

# Restart ComfyUI
```

## Usage

### Resolution Selector Plus v2

**Add Node:** `Add Node > utils > Resolution Selector Plus v2`

Each slot has these controls. Slot 1 is required; slots 2 through 4 appear as you activate preceding slots.
The node displays names such as "Res 1 model" and "Res 2 aspect ratio"; workflow input IDs remain `resN_model` and `resN_aspect_ratio`.
Resolution labels are compact, for example `1280x704 (16:9)`, with no orientation text.

| Input | Choices and default | Meaning |
| --- | --- | --- |
| `res1_model` through `res4_model` | Models below; default SDXL | Sets each slot's latent channels, spatial downscale, and tensor shape. |
| `res1_aspect_ratio` through `res4_aspect_ratio` | 1:1, 5:4, 4:3, 3:2, 16:10, 16:9, 2:1, 21:9, 12:5, 3:1, 3:4, 2:3, 5:8, 9:16, 1:2, 5:12, 1:3; default 1:1 | Filters each slot's resolution list. |
| `res1_megapixels` through `res4_megapixels` | 0.25, 0.5, 1.0, 1.5, 2.0, 4.0; default 1.0 | Filters each slot's resolution list. |
| `res1_resolution` through `res4_resolution` | Up to three base candidates near 90%, 100%, and 110% of target area. Each target snaps to 64 pixels; if its result has a different labeled ratio, it retries at 32, 16, then 8 pixels. Duplicate candidates appear once. Slot 1 defaults to the first 1:1, 1.0 MP candidate; later slots default to `none`. | Selects a base resolution. |
| `res1_multiple` through `res4_multiple` | 8, 16, 32, 64; default 8 | Rounds that slot's width and height to the nearest multiple, with half values rounded up and a minimum of one multiple. |

Changing a slot's `resN_model` sets its `resN_multiple` to the best multiple below. You can change it afterward; saved overrides remain on reload. If it is smaller than that model's latent downscale, latent dimensions use integer division and the node logs a note.

| Model | Channels | Downscale | Best multiple | Other models with the same latent format |
| --- | ---: | ---: | ---: | --- |
| SD 1.5 | 4 | 8 | 8 | SD 2, SSD-1B |
| SDXL | 4 | 8 | 8 | Vega, KOALA |
| SD3 | 16 | 8 | 16 | None listed |
| Flux.1 | 16 | 8 | 16 | Chroma, Z-Image, HiDream |
| Flux.2 | 128 | 16 | 16 | Flux.3, Ideogram4 |
| Chroma | 16 | 8 | 16 | Flux.1, Z-Image |
| Z-Image | 16 | 8 | 16 | Flux.1, HiDream |
| Qwen-Image | 16 | 8 | 16 | Krea2, Anima, JoyImage (5D, one frame) |
| Qwen-Image 2.1 | 64 | 16 | 16* | None listed |
| HiDream | 16 | 8 | 16 | Flux.1, Chroma |
| HunyuanImage 2.1 | 64 | 32 | 32* | None listed |
| Other (4ch /8) | 4 | 8 | 8 | PixArt, AuraFlow |

*Patch size is unverified for this model; the best multiple falls back to its downscale.

Set `res2_resolution` beyond `none` to reveal its output triple and the next selector. Repeat through res4. Setting an earlier slot to `none` clears later slots and their links. Saved workflows retain active slot selections and links.
If an older v2 workflow contains invalid or shifted widget values, the frontend restores those controls to defaults and warns once for that node. Python still rejects invalid values at execution.

| Slot | Outputs |
| --- | --- |
| 1 | `res1_width` (INT), `res1_height` (INT), `res1_latent` (LATENT) |
| 2 | `res2_width` (INT), `res2_height` (INT), `res2_latent` (LATENT) |
| 3 | `res3_width` (INT), `res3_height` (INT), `res3_latent` (LATENT) |
| 4 | `res4_width` (INT), `res4_height` (INT), `res4_latent` (LATENT) |

Outputs are named `res1_width`, `res1_height`, `res1_latent`, through `res4_latent`.

**Examples:**

```text
Resolution Selector Plus v2 (res1_model: SD3, res1_aspect_ratio: 16:9, res1_megapixels: 1.0)
  -> choose a 16:9 resolution near 1 MP -> res1_latent -> KSampler

Resolution Selector Plus v2 (res1_model: SDXL, res1_aspect_ratio: 1:1, res1_megapixels: 1.0,
  res2_model: Qwen-Image 2.1, res2_aspect_ratio: 9:16, res2_megapixels: 0.5,
  res2_resolution: chosen portrait candidate)
  -> res1_width / res1_height / res1_latent for the square branch
  -> res2_width / res2_height / res2_latent for the portrait branch
```

## Legacy: Resolution Selector Plus (deprecated)

![Resolution Selector Plus (deprecated) node](node_preview_v1.png)

The original `ResolutionSelectorPlus` node remains available for saved workflows. Its inputs and six outputs work as before.

**Add Node:** `Add Node > utils > Resolution Selector Plus (deprecated)`

**Inputs:**
- `model` (dropdown) - Select your image generation model or "All" for all resolutions
- `resolution` (dropdown) - Choose from model-optimized presets with aspect ratios (e.g., "1920x1080 (16:9 Landscape)")
- `resolution_multiplier` (dropdown) - Multiply preset resolution (1x, 2x, 3x, 4x)
- `batch_size` (number) - Number of latent samples to generate (1-64, default: 1)
- `custom_width` (optional) - Override with custom width (0-4096, step 8)
- `custom_height` (optional) - Override with custom height (0-4096, step 8)
- `custom_multiplier` (optional) - Independent multiplier for custom dimensions (1x, 2x, 3x, 4x)
- `custom_batch` (optional) - Number of latent samples for custom resolution (1-64, default: 1)

**Outputs:**
- `width` (INT) - Preset resolution width in pixels
- `height` (INT) - Preset resolution height in pixels
- `latent` (LATENT) - Empty latent tensor for preset resolution (batch_size samples)
- `custom_width` (INT) - Custom width (0 if not set)
- `custom_height` (INT) - Custom height (0 if not set)
- `custom_latent` (LATENT) - Empty latent tensor for custom resolution (custom_batch samples)

**Example Workflows:**

**Basic preset with multiplier:**
```
Resolution Selector Plus (model: SDXL, resolution: "1024x1024 (1:1 Square)", multiplier: 2x)
  -> width: 2048, height: 2048
  -> latent -> KSampler
```

**Custom dimensions with independent multiplier:**
```
Resolution Selector Plus (custom_width: 1024, custom_height: 768, custom_multiplier: 2x)
  -> custom_width: 2048, custom_height: 1536
  -> custom_latent -> KSampler
```

**Using "All" model option:**
```
Resolution Selector Plus (model: All, resolution: "1920x1080 (16:9 Landscape)")
  -> Shows all 76 unique resolutions from all models
```

---

## Compatibility

Dual API: exports the legacy V1 `NODE_CLASS_MAPPINGS` and a V3 `comfy_entrypoint` (`comfy_api`). Verified on ComfyUI 0.25.0. On builds whose loader reads `NODE_CLASS_MAPPINGS` first, the V1 path is used and `comfy_entrypoint` is skipped, so nodes are not registered twice.

## Support

If you find this useful, please consider [starring the repo](https://github.com/bradsec/ComfyUI_ResolutionSelectorPlus). Stars help other people discover these nodes.
