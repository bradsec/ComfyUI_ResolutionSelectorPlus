"""Image model choices from ComfyUI, with a snapshot for standalone use."""

import json
from pathlib import Path


# Released labels are workflow values. Keep their spelling and relative order.
RELEASED = {
    "SD15": ("SD 1.5", 8), "SDXL": ("SDXL", 8), "SD3": ("SD3", 16),
    "Flux": ("Flux.1", 16), "Flux2": ("Flux.2", 16),
    "Chroma": ("Chroma", 16), "ZImage": ("Z-Image", 16),
    "QwenImage": ("Qwen-Image", 16), "QwenImage21": ("Qwen-Image 2.1", 16),
    "HiDream": ("HiDream", 16), "HunyuanImage21": ("HunyuanImage 2.1", 32),
}
RELEASED_ORDER = ["SD 1.5", "SDXL", "SD3", "Flux.1", "Flux.2", "Chroma",
                  "Z-Image", "Qwen-Image", "Qwen-Image 2.1", "HiDream",
                  "HunyuanImage 2.1"]
FRIENDLY = {
    "Flux3": "Flux.3", "MOSSImage": "MOSS-Image", "Ideogram4": "Ideogram 4",
    "Krea2": "Krea 2", "Anima": "Anima", "JoyImage": "JoyImage",
    "AuraFlow": "AuraFlow", "Boogu": "Boogu", "ChromaRadiance": "Chroma Radiance",
    "CosmosT2IPredict2": "Cosmos Predict2", "ErnieImage": "ERNIE-Image",
    "Fibo2": "FIBO 2", "FluxSchnell": "Flux.1 Schnell", "HiDreamO1": "HiDream-O1",
    "HunyuanDiT": "Hunyuan-DiT", "HunyuanDiT1": "Hunyuan-DiT",
    "Kandinsky5Image": "Kandinsky 5 Image", "Lens": "Lens",
    "LongCatImage": "LongCat-Image", "Lumina2": "Lumina Image 2.0",
    "MageFlow": "Mage Flow", "MingImage": "Ming-Image", "Omnigen2": "OmniGen2",
    "PixArtAlpha": "PixArt-Alpha", "PixArtSigma": "PixArt-Sigma",
    "PixelDiTT2I": "PixelDiT", "SenseNovaU15": "SenseNova U1.5",
    "KOALA_700M": "KOALA", "KOALA_1B": "KOALA", "SD20": "SD 2.x",
    "SSD1B": "SSD-1B", "Segmind_Vega": "Segmind Vega",
}
CURATED_EXTRA_ORDER = list(dict.fromkeys(FRIENDLY.values()))
# Research: 07-researchanalyst-multiples.md S1-S17, local ComfyUI bdb0816a2.
# HIGH: omnigen/omnigen2.py:273; krea2/model.py:287; hidream_o1/model.py:28; pixeldit/model.py:133;
# model_detection.py:594-596 (Lumina2); joyimage/model.py:251; aura/mmdit.py:316;
# cosmos/predict2.py:642; flux/model.py:317; pixart/pixartms.py:73.
# MED/HIGH: kandinsky5/model.py:286; boogu/model.py:175.
# MED: model_detection.py:343 (Chroma Radiance checkpoint patch), :594,633 (Ming);
# flux3/model.py:216; moss_image/model.py:274; qwen_image21/model.py:406;
# supported_models.py:2259 (HunyuanImage21); ernie/model.py:205.
# MED Chroma Radiance patch 16 is checkpoint-dependent; prefer checkpoint review if changed.
# LOW label confidence: MOSS-Image, JoyImage, FIBO 2, Boogu, Mage Flow.
MED_CONFIDENCE_CLASSES = {"QwenImage21", "HunyuanImage21", "Flux3", "MOSSImage",
                          "Ideogram4", "Boogu", "ChromaRadiance", "ErnieImage",
                          "Fibo2", "Kandinsky5Image", "Lens", "MingImage"}
BEST_MULTIPLES = {
    "QwenImage21": 16, "HunyuanImage21": 32, "Flux3": 16,
    "MOSSImage": 16, "Ideogram4": 16, "Krea2": 16, "Anima": 16,
    "JoyImage": 16, "AuraFlow": 16, "Boogu": 16, "ChromaRadiance": 16,
    "CosmosT2IPredict2": 16, "ErnieImage": 16, "Fibo2": 16,
    "FluxSchnell": 16, "HiDreamO1": 32, "HunyuanDiT": 16,
    "HunyuanDiT1": 16, "Kandinsky5Image": 16, "Lens": 16,
    "LongCatImage": 16, "Lumina2": 16, "MageFlow": 16,
    "MingImage": 16, "Omnigen2": 16, "PixArtAlpha": 16,
    "PixArtSigma": 16, "PixelDiTT2I": 16, "SenseNovaU15": 32,
    "KOALA_700M": 8, "KOALA_1B": 8, "SD20": 8,
    "SSD1B": 8, "Segmind_Vega": 8,
}
INCLUDE_3D = {"QwenImage", "Krea2", "Anima", "JoyImage", "CosmosT2IPredict2", "MingImage"}
EXCLUDE = {
    "LotusD", "Stable_Zero123", "SD15_instructpix2pix", "SD21UnclipL", "SD21UnclipH",
    "SDXL_instructpix2pix", "SDXLRefiner", "SD_X4Upscaler", "Stable_Cascade_C",
    "Stable_Cascade_B", "SV3D_u", "SV3D_p", "FluxInpaint", "HunyuanImage21Refiner",
    "ZImagePixelSpace", "GenmoMochi", "LTXV", "LTXAV", "MiniMaxH3",
    "HunyuanVideo15_SR_Distilled", "HunyuanVideo15", "HunyuanVideoSkyreelsI2V",
    "HunyuanVideoI2V", "HunyuanVideo", "CosmosT2V", "CosmosI2V",
    "CosmosI2VPredict2", "WAN22_T2V", "WAN21_CausalAR_T2V", "WAN21_T2V",
    "WAN21_I2V", "WAN21_FunControl2V", "WAN21_Vace", "WAN21_Camera",
    "WAN22_Camera", "WAN22_S2V", "WAN21_HuMo", "WAN22_Animate",
    "WAN_Animate2", "WAN21_FlowRVS", "WAN21_SCAIL", "WAN21_SCAIL2",
    "WAN22_RelayVSR", "WAN22_WanDancer", "Hunyuan3Dv2mini", "Hunyuan3Dv2",
    "Hunyuan3Dv2_1", "TripoSplat", "SeedVR2", "ACEStep", "ACEStep15",
    "MiniMaxMusic3", "YuE2", "Kandinsky5", "RT_DETR_v4", "SAM3", "SAM31",
    "CogVideoX_Inpaint", "CogVideoX_I2V", "CogVideoX_T2V", "SVD_img2vid",
    "Trellis2", "DepthAnything3", "PiD",
}


# Same choices as the node's rounding multiple (nodes.V2_MULTIPLES).
MULTIPLE_CHOICES = (8, 16, 32, 64)


def default_best_multiple(downscale):
    """Smallest rounding multiple that keeps latent sizes whole: 8 for /1 and /4."""
    return next((m for m in MULTIPLE_CHOICES if m >= downscale), MULTIPLE_CHOICES[-1])


def snapshot_classes():
    data = json.loads(Path(__file__).with_name("model_snapshot.json").read_text())
    classes = []
    for name, (format_name, channels, downscale, dimensions) in data.items():
        latent = type(format_name, (), {"latent_channels": channels,
                    "spacial_downscale_ratio": downscale, "latent_dimensions": dimensions})
        classes.append(type(name, (), {"latent_format": latent}))
    return classes


def discover_models(classes=None):
    if classes is None:
        try:
            from comfy.supported_models import models
            classes = models
        except ImportError:
            classes = snapshot_classes()
    found = {}
    for cls in classes:
        name = cls.__name__
        latent = getattr(cls, "latent_format", None)
        dimensions = getattr(latent, "latent_dimensions", None)
        if name in EXCLUDE or not (dimensions == 2 or name in INCLUDE_3D):
            continue
        channels = getattr(latent, "latent_channels", None)
        downscale = getattr(latent, "spacial_downscale_ratio", None)
        if not isinstance(channels, int) or not isinstance(downscale, int) or downscale < 1:
            continue
        found.setdefault(*_entry(name, latent.__name__, channels, downscale, dimensions))
    # Every curated label stays selectable when the installed ComfyUI lacks its
    # class (upstream rename or removal), so saved workflow values never vanish.
    curated = {label for label, _ in RELEASED.values()} | set(FRIENDLY.values())
    if curated - set(found):
        for cls in snapshot_classes():
            name = cls.__name__
            label = RELEASED[name][0] if name in RELEASED else FRIENDLY.get(name)
            if label and label not in found:
                latent = cls.latent_format
                found[label] = _entry(name, latent.__name__, latent.latent_channels,
                                      latent.spacial_downscale_ratio, latent.latent_dimensions)[1]
    # Other is a compatibility choice, independent of installed model classes.
    found["Other (4ch /8)"] = ("SD15", (4, 8, 4), 8)
    known = set(RELEASED_ORDER) | set(CURATED_EXTRA_ORDER) | {"Other (4ch /8)"}
    return {label: found[label] for label in
            [*RELEASED_ORDER, *CURATED_EXTRA_ORDER, *sorted(set(found) - known),
             "Other (4ch /8)"] if label in found}


def _entry(name, format_name, channels, downscale, dimensions):
    label, best = RELEASED.get(name, (FRIENDLY.get(name, name),
                                      BEST_MULTIPLES.get(name, default_best_multiple(downscale))))
    return label, (format_name, (channels, downscale, dimensions + 2), best)
