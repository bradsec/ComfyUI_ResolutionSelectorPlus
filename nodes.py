import math
import torch

try:
    from .model_discovery import discover_models
except ImportError:  # loaded as a plain module (unit tests)
    from model_discovery import discover_models

try:
    import comfy.model_management
    COMFY_AVAILABLE = True
except ImportError:
    COMFY_AVAILABLE = False


# Model-specific resolution presets with constraints
# Includes: model-optimized sizes + photo print (4x6, 5x7, 8x10) + digital/social + canvas art ratios
MODEL_RESOLUTIONS = {
    "Flux": {
        "square": [(512, 512), (768, 768), (1024, 1024), (1088, 1088), (1280, 1280), (1328, 1328), (1536, 1536), (1920, 1920), (2048, 2048)],
        "portrait": [(688, 2048), (768, 1344), (832, 1216), (896, 1152), (928, 1664), (1024, 1536), (1024, 1792), (1024, 2048), (1056, 1584), (1088, 1920), (1104, 1472), (1152, 2048), (1200, 1792), (1360, 2048), (1456, 2048), (1536, 2048), (1616, 2048), (1632, 2048), (1712, 2048)],
        "landscape": [(1280, 720), (1344, 768), (1216, 832), (1152, 896), (1472, 1104), (1536, 1024), (1584, 1056), (1664, 928), (1792, 1024), (1792, 1200), (1920, 1088), (2048, 688), (2048, 1024), (2048, 1152), (2048, 1360), (2048, 1456), (2048, 1536), (2048, 1616), (2048, 1632), (2048, 1712)],
        "constraints": {"divisible_by": 16, "min": 256, "max": 2048, "latent_channels": 16}
    },
    "Qwen Image": {
        "square": [(1024, 1024), (1080, 1080), (1280, 1280), (1328, 1328), (1536, 1536), (1920, 1920), (2048, 2048)],
        "portrait": [(680, 2048), (928, 1664), (1024, 1536), (1024, 2048), (1056, 1584), (1080, 1920), (1104, 1472), (1152, 2048), (1200, 1800), (1368, 2048), (1464, 2048), (1536, 2048), (1608, 2048), (1640, 2048), (1704, 2048)],
        "landscape": [(1280, 720), (1472, 1104), (1536, 1024), (1584, 1056), (1664, 928), (1800, 1200), (1920, 1080), (2048, 680), (2048, 1024), (2048, 1152), (2048, 1368), (2048, 1464), (2048, 1536), (2048, 1608), (2048, 1640), (2048, 1704)],
        "constraints": {"divisible_by": 8, "min": 256, "max": 2048, "latent_channels": 16}
    },
    "Z-Image": {
        "square": [(512, 512), (768, 768), (1024, 1024), (1080, 1080), (1280, 1280), (1328, 1328), (1536, 1536), (1920, 1920), (2048, 2048)],
        "portrait": [(680, 2048), (720, 1280), (768, 1024), (928, 1664), (1024, 2048), (1056, 1584), (1080, 1920), (1104, 1472), (1152, 2048), (1200, 1800), (1368, 2048), (1464, 2048), (1536, 2048), (1608, 2048), (1640, 2048), (1704, 2048)],
        "landscape": [(1024, 768), (1280, 720), (1472, 1104), (1584, 1056), (1664, 928), (1800, 1200), (1920, 1080), (2048, 680), (2048, 1024), (2048, 1152), (2048, 1368), (2048, 1464), (2048, 1536), (2048, 1608), (2048, 1640), (2048, 1704)],
        "constraints": {"divisible_by": 8, "min": 256, "max": 2048, "latent_channels": 16}
    },
    "SD 1.5": {
        "square": [(512, 512), (768, 768), (1024, 1024), (1080, 1080), (1280, 1280), (1536, 1536)],
        "portrait": [(512, 768), (512, 680), (512, 1024), (680, 2048), (768, 1024), (768, 1344), (1024, 2048), (1080, 1920), (1200, 1800), (1368, 2048), (1464, 2048), (1536, 2048), (1608, 2048), (1640, 2048), (1704, 2048)],
        "landscape": [(768, 512), (1024, 512), (1024, 768), (1280, 720), (1344, 768), (1536, 512), (1800, 1200), (1920, 1080), (2048, 680), (2048, 1024), (2048, 1368), (2048, 1464), (2048, 1536), (2048, 1608), (2048, 1640), (2048, 1704)],
        "constraints": {"divisible_by": 8, "min": 256, "max": 2048, "latent_channels": 4}
    },
    "SDXL": {
        "square": [(1024, 1024), (1080, 1080), (1280, 1280), (1536, 1536), (1920, 1920), (2048, 2048)],
        "portrait": [(640, 1536), (680, 2048), (768, 1344), (832, 1216), (896, 1152), (1024, 1536), (1024, 2048), (1080, 1920), (1152, 2048), (1200, 1800), (1368, 2048), (1464, 2048), (1536, 2048), (1608, 2048), (1640, 2048), (1704, 2048)],
        "landscape": [(1152, 896), (1216, 832), (1280, 720), (1344, 768), (1536, 640), (1536, 1024), (1800, 1200), (1920, 1080), (2048, 680), (2048, 1024), (2048, 1152), (2048, 1368), (2048, 1464), (2048, 1536), (2048, 1608), (2048, 1640), (2048, 1704)],
        "constraints": {"divisible_by": 8, "min": 256, "max": 2048, "latent_channels": 4}
    }
}


def calculate_aspect_ratio(width, height):
    """
    Calculate simplified aspect ratio from dimensions, using nearest common ratio.

    Args:
        width (int): Width in pixels
        height (int): Height in pixels

    Returns:
        str: Aspect ratio like "16:9" or "1:1"
    """
    # Calculate actual ratio as decimal
    actual_ratio = width / height

    # Common aspect ratios (ratio_value, "width:height" string)
    common_ratios = [
        (1.0, "1:1"),      # Square
        (1.25, "5:4"),     # 1.25
        (1.33, "4:3"),     # 1.333...
        (1.5, "3:2"),      # 1.5
        (1.6, "16:10"),    # 1.6
        (1.78, "16:9"),    # 1.777...
        (2.0, "2:1"),      # 2.0
        (2.35, "21:9"),    # 2.333... (ultrawide)
        (2.4, "12:5"),     # 2.4
        (3.0, "3:1"),      # 3.0
        # Portrait ratios
        (0.75, "3:4"),     # 0.75
        (0.67, "2:3"),     # 0.666...
        (0.625, "5:8"),    # 0.625
        (0.56, "9:16"),    # 0.5625
        (0.5, "1:2"),      # 0.5
        (0.42, "5:12"),    # 0.4166...
        (0.33, "1:3"),     # 0.333... (panoramic)
    ]

    # Find closest common ratio by absolute difference
    closest_ratio = min(common_ratios, key=lambda r: abs(actual_ratio - r[0]))
    return closest_ratio[1]


def format_resolution(width, height):
    """
    Format resolution tuple into display string with aspect ratio and orientation.
    Uses fixed-width formatting for better alignment in dropdowns.

    Args:
        width (int): Width in pixels
        height (int): Height in pixels

    Returns:
        str: Formatted string like "1920x1080  (16:9 Landscape)" with consistent spacing
    """
    aspect_ratio = calculate_aspect_ratio(width, height)

    if width == height:
        orientation = "Square"
    elif width < height:
        orientation = "Portrait"
    else:
        orientation = "Landscape"

    # Format with fixed width for better alignment (e.g., "1920x1080  ")
    # Most resolutions are 4 digits, so we pad to 9 characters (4x4 + 'x')
    resolution_str = f"{width}x{height}"
    padded_resolution = resolution_str.ljust(13)  # Pad to 13 chars for alignment

    return f"{padded_resolution}({aspect_ratio} {orientation})"


def get_resolution_list(model_name):
    """
    Generate ordered list of resolution strings for a specific model.

    Args:
        model_name (str): Name of the model (or "All" for all unique resolutions)

    Returns:
        list: Formatted resolution strings in order: square, portrait, landscape
    """
    if model_name == "All":
        return get_all_resolutions()
    if model_name in V2_MODELS and model_name not in LEGACY_EQUIVALENTS:
        # Discovered models use the All list limited to presets their best
        # multiple divides, the same rule _validate_dimensions enforces.
        best = V2_MODELS[model_name][2]
        return [label for label in get_all_resolutions()
                if all(side % best == 0 for side in parse_resolution_string(label))]

    if model_name not in MODEL_RESOLUTIONS:
        return []

    model_data = MODEL_RESOLUTIONS[model_name]
    resolutions = []

    # Order: square first, then portrait, then landscape
    for category in ["square", "portrait", "landscape"]:
        for width, height in model_data[category]:
            resolutions.append(format_resolution(width, height))

    return resolutions


def get_default_resolution(model_name):
    """
    Get the default/native resolution for a specific model.

    Args:
        model_name (str): Name of the model

    Returns:
        str: Formatted resolution string for the model's native resolution
    """
    # Model-specific native/optimal resolutions
    default_resolutions = {
        "Flux": (1024, 1024),      # Flux native
        "Qwen Image": (1328, 1328), # Qwen native
        "Z-Image": (1024, 1024),    # Z-Image native
        "SD 1.5": (512, 512),       # SD 1.5 native
        "SDXL": (1024, 1024),       # SDXL native
        "All": (1024, 1024),        # Default for "All"
    }

    if model_name in default_resolutions:
        width, height = default_resolutions[model_name]
        return format_resolution(width, height)

    # Fallback to 1024x1024
    return format_resolution(1024, 1024)


def get_latent_channels(model_name):
    """
    Return the latent channel count for a model, including discovered models.

    SD 1.5 and SDXL use 4-channel latents. Flux, Qwen Image, and Z-Image use
    16-channel latents. A wrong channel count makes the LATENT output unusable
    with that model's sampler.

    For "All" (no specific model) this defaults to 4 for backward compatibility
    with SD-based workflows; pick the specific model to get a 16-channel latent.

    Args:
        model_name (str): Model name, or "All".

    Returns:
        int: Latent channel count.
    """
    if model_name in V2_MODELS and model_name not in LEGACY_EQUIVALENTS:
        return V2_MODEL_FORMATS[model_name][0]
    model_data = MODEL_RESOLUTIONS.get(model_name)
    if model_data:
        return model_data["constraints"].get("latent_channels", 4)
    return 4


def get_all_resolutions():
    """
    Get all unique resolution strings across all models, sorted by dimensions.

    Returns:
        list: All unique resolution strings sorted by total pixels
    """
    unique_resolutions = {}

    # Collect all unique width×height pairs
    for model_name in MODEL_RESOLUTIONS.keys():
        model_data = MODEL_RESOLUTIONS[model_name]
        for category in ["square", "portrait", "landscape"]:
            for width, height in model_data[category]:
                key = (width, height)
                if key not in unique_resolutions:
                    unique_resolutions[key] = format_resolution(width, height)

    # Sort by total pixels, then by width
    sorted_resolutions = sorted(
        unique_resolutions.items(),
        key=lambda item: (item[0][0] * item[0][1], item[0][0])
    )

    return [res_str for _, res_str in sorted_resolutions]


def parse_resolution_string(resolution_str):
    """
    Parse formatted resolution string back to width, height integers.

    Args:
        resolution_str (str): Format "1920x1080  (16:9 Landscape)" with possible padding

    Returns:
        tuple: (width, height)

    Raises:
        ValueError: If string format is invalid
    """
    try:
        # Format: "1920x1080  (16:9 Landscape)" - may have padding spaces
        # Extract the dimension part (before the opening parenthesis)
        dimension_part = resolution_str.split("(")[0].strip()

        if not dimension_part or 'x' not in dimension_part:
            raise ValueError(f"No dimension part found in: {resolution_str}")

        # Split on 'x' and convert to integers
        width, height = map(int, dimension_part.split("x"))

        return (width, height)
    except (ValueError, IndexError) as e:
        raise ValueError(f"Invalid resolution format: {resolution_str}")


# Tooltips (shared by both API wrappers).
TIP_MODEL  = "Image model. Existing models keep their presets; discovered models and 'All' show every preset."
TIP_RESOLUTION = "Preset resolution. The list filters to the selected model."
TIP_MULT   = "Multiplies the preset width and height (1x to 4x)."
TIP_BATCH  = "Number of latent samples in the preset latent batch."
TIP_CW     = "Custom width in pixels. 0 disables the custom outputs. Must satisfy the model's divisibility and bounds."
TIP_CH     = "Custom height in pixels. 0 disables the custom outputs. Must satisfy the model's divisibility and bounds."
TIP_CMULT  = "Multiplies the custom width and height (1x to 4x)."
TIP_CBATCH = "Number of latent samples in the custom latent batch."

OUTPUT_TIPS = {
    "width": "Preset width in pixels after multiplier.",
    "height": "Preset height in pixels after multiplier.",
    "latent": "Empty latent for the preset resolution.",
    "custom_width": "Custom width after multiplier, or 0 when custom is disabled.",
    "custom_height": "Custom height after multiplier, or 0 when custom is disabled.",
    "custom_latent": "Empty latent for the custom resolution.",
}


class ResolutionSelector:
    """
    Enhanced resolution selector supporting multiple image generation models.
    Provides model-specific resolution presets, custom dimension inputs, and empty latent output.
    """
    DESCRIPTION = "Resolution Selector Plus (Legacy): preset sizes and custom latents. Use Resolution Selector Plus for new workflows."

    def __init__(self):
        """Initialize device for latent tensor generation."""
        if COMFY_AVAILABLE:
            self.device = comfy.model_management.intermediate_device()
        else:
            self.device = torch.device("cpu")

    @classmethod
    def INPUT_TYPES(cls):
        """
        Return a dictionary which contains config for all input fields.

        Returns:
            dict: Input configuration with required and optional fields
        """
        model_list = ["All"] + list(MODEL_RESOLUTIONS) + [name for name in V2_MODELS
                                                         if name not in LEGACY_EQUIVALENTS and name != "Other (4ch /8)"]

        # Get all possible resolutions across all models (JavaScript will filter dynamically)
        all_resolutions = get_all_resolutions()

        return {
            "required": {
                "model": (model_list, {
                    "default": "SDXL",
                    "tooltip": TIP_MODEL,
                    "model_info": {name: {"best_multiple": V2_MODELS[name][2]} for name in model_list
                                   if name in V2_MODELS and name not in LEGACY_EQUIVALENTS},
                }),
                "resolution": (all_resolutions, {
                    "default": format_resolution(1024, 1024),
                    "tooltip": TIP_RESOLUTION,
                }),
                "resolution_multiplier": (["1x", "2x", "3x", "4x"], {
                    "default": "1x",
                    "tooltip": TIP_MULT,
                }),
                "batch_size": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 64,
                    "step": 1,
                    "display": "number",
                    "tooltip": TIP_BATCH,
                }),
            },
            "optional": {
                "custom_width": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 4096,
                    "step": 8,
                    "display": "number",
                    "tooltip": TIP_CW,
                }),
                "custom_height": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 4096,
                    "step": 8,
                    "display": "number",
                    "tooltip": TIP_CH,
                }),
                "custom_multiplier": (["1x", "2x", "3x", "4x"], {
                    "default": "1x",
                    "tooltip": TIP_CMULT,
                }),
                "custom_batch": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 64,
                    "step": 1,
                    "display": "number",
                    "tooltip": TIP_CBATCH,
                }),
            }
        }

    RETURN_TYPES = ("INT", "INT", "LATENT", "INT", "INT", "LATENT")
    RETURN_NAMES = ("width", "height", "latent", "custom_width", "custom_height", "custom_latent")
    OUTPUT_TOOLTIPS = tuple(OUTPUT_TIPS[name] for name in RETURN_NAMES)
    FUNCTION = "select_resolution"
    CATEGORY = "utils"

    def select_resolution(self, model, resolution, resolution_multiplier="1x", batch_size=1, custom_width=0, custom_height=0, custom_multiplier="1x", custom_batch=1):
        """
        Select and validate resolution, generate outputs.

        Args:
            model (str): Selected model name
            resolution (str): Selected preset resolution string
            resolution_multiplier (str): Multiplier for resolution (1x-4x)
            batch_size (int): Number of latent samples for preset resolution (default: 1)
            custom_width (int, optional): Custom width override
            custom_height (int, optional): Custom height override
            custom_multiplier (str, optional): Multiplier for custom dimensions (1x-4x)
            custom_batch (int, optional): Number of latent samples for custom resolution (default: 1)

        Returns:
            tuple: (width: int, height: int, latent: dict, custom_width: int, custom_height: int, custom_latent: dict)
        """
        # Parse multipliers (e.g., "2x" -> 2)
        multiplier = int(resolution_multiplier.replace("x", ""))
        custom_mult = int(custom_multiplier.replace("x", ""))

        # Parse preset resolution
        width, height = parse_resolution_string(resolution)

        # The resolution combo lists every model's presets (the JS extension
        # filters client-side), so API-built workflows can pair a model with a
        # preset that violates its constraints. Validate before the multiplier:
        # multiplied presets intentionally exceed the max constraint, and an
        # integer multiplier preserves divisibility.
        self._validate_dimensions(model, width, height)

        # Apply multiplier to preset resolution
        width *= multiplier
        height *= multiplier

        # Channel count depends on the model (4 for SD1.5/SDXL, 16 for Flux/Qwen/Z-Image)
        channels = get_latent_channels(model)

        # Generate latent for preset resolution with batch size
        latent = self._generate_model_latent(model, width, height, batch_size, channels)

        # Determine final custom dimensions
        if custom_width > 0 and custom_height > 0:
            # Use custom dimensions with custom multiplier
            final_custom_width = custom_width * custom_mult
            final_custom_height = custom_height * custom_mult

            # Validate against model constraints. "All" still gets the generic
            # 8-divisible / bounds check so the latent dimensions are not silently
            # truncated by the //8 below.
            self._validate_dimensions(model, final_custom_width, final_custom_height)

            # Generate custom latent with custom batch size
            custom_latent = self._generate_model_latent(model, final_custom_width, final_custom_height, custom_batch, channels)

            return (width, height, latent, final_custom_width, final_custom_height, custom_latent)
        else:
            # No custom dimensions: return zeros and a minimal VALID latent (8x8 -> 1x1
            # in latent space), never a zero-size [B,C,0,0] tensor.
            custom_latent = self._generate_model_latent(model, 8, 8, 1, channels)

            return (width, height, latent, 0, 0, custom_latent)

    def _validate_dimensions(self, model, width, height):
        """
        Validate dimensions against model-specific constraints.

        Args:
            model (str): Model name
            width (int): Width in pixels
            height (int): Height in pixels

        Raises:
            ValueError: If dimensions violate model constraints
        """
        if model in V2_MODELS and model not in LEGACY_EQUIVALENTS:
            constraints = {"divisible_by": V2_MODELS[model][2], "min": 64, "max": 4096}
        elif model in MODEL_RESOLUTIONS:
            constraints = MODEL_RESOLUTIONS[model]["constraints"]
        else:
            # "All" or unknown model: enforce the generic latent requirement so
            # dimensions divide cleanly by 8 and stay within sane bounds.
            constraints = {"divisible_by": 8, "min": 64, "max": 4096}

        divisible_by = constraints.get("divisible_by", 8)
        min_dim = constraints.get("min", 64)
        max_dim = constraints.get("max", 4096)

        # Check divisibility
        if width % divisible_by != 0:
            raise ValueError(
                f"{model} requires width divisible by {divisible_by}. "
                f"Got {width} (remainder: {width % divisible_by})"
            )

        if height % divisible_by != 0:
            raise ValueError(
                f"{model} requires height divisible by {divisible_by}. "
                f"Got {height} (remainder: {height % divisible_by})"
            )

        # Check bounds
        if width < min_dim or width > max_dim:
            raise ValueError(
                f"{model} requires width between {min_dim} and {max_dim}. Got {width}"
            )

        if height < min_dim or height > max_dim:
            raise ValueError(
                f"{model} requires height between {min_dim} and {max_dim}. Got {height}"
            )

    def _generate_empty_latent(self, width, height, batch_size=1, channels=4):
        """
        Generate empty latent tensor for VAE input.

        Args:
            width (int): Image width in pixels
            height (int): Image height in pixels
            batch_size (int): Number of latent samples (default: 1)
            channels (int): Latent channel count (4 for SD1.5/SDXL, 16 for Flux/Qwen/Z-Image)

        Returns:
            dict: LATENT dict with 'samples' key containing empty tensor
        """
        # Latent space is 1/8 the image dimensions for SD-based models
        latent_width = width // 8
        latent_height = height // 8

        # Shape: [batch_size, channels, height//8, width//8]
        latent_tensor = torch.zeros(
            [batch_size, channels, latent_height, latent_width],
            device=self.device
        )

        return {"samples": latent_tensor}

    def _generate_model_latent(self, model, width, height, batch_size, channels):
        if model not in V2_MODELS or model in LEGACY_EQUIVALENTS:
            return self._generate_empty_latent(width, height, batch_size, channels)
        _, downscale, rank = V2_MODEL_FORMATS[model]
        shape = [batch_size, channels, max(1, height // downscale), max(1, width // downscale)]
        if rank == 5:
            shape.insert(2, 1)
        kwargs = {"device": self.device}
        if model == "SD3" and COMFY_AVAILABLE:
            kwargs["dtype"] = comfy.model_management.intermediate_dtype()
        return {"samples": torch.zeros(shape, **kwargs), "downscale_ratio_spacial": downscale}


# label -> (comfy.latent_formats class, fallback (channels, downscale, rank), best pixel multiple).
# Built by model_discovery.discover_models(); sources, confidence and the
# include/exclude rules are documented in model_discovery.py.
V2_MODELS = discover_models()
LEGACY_EQUIVALENTS = {"Flux.1", "Qwen-Image", "Z-Image", "SD 1.5", "SDXL"}


def load_v2_model_formats():
    try:
        import comfy.latent_formats as latent_formats
    except ImportError:
        latent_formats = None
    formats = {}
    for model, (class_name, fallback, _) in V2_MODELS.items():
        latent = getattr(latent_formats, class_name, None) if latent_formats else None
        formats[model] = (latent.latent_channels, latent.spacial_downscale_ratio,
                          latent.latent_dimensions + 2) if latent else fallback
    return formats


V2_MODEL_FORMATS = load_v2_model_formats()
V2_RATIOS = ("1:1 (Square)", "5:4 (Large Format)", "4:3 (Standard)",
             "3:4 (Portrait Standard)", "3:2 (Photo)", "2:3 (Portrait Photo)",
             "16:10 (Widescreen Monitor)", "5:8 (Portrait Widescreen Monitor)",
             "16:9 (Widescreen)", "9:16 (Portrait Widescreen)", "2:1 (Univisium)",
             "1:2 (Portrait Univisium)", "21:9 (Ultrawide)", "12:5 (Cinemascope)",
             "5:12 (Portrait Cinemascope)", "3:1 (Panorama)", "1:3 (Portrait Panorama)")
V2_RATIO_BY_BARE = {name.split(" ", 1)[0]: name for name in V2_RATIOS}
V2_MEGAPIXELS = ("0.25", "0.5", "1.0", "1.5", "2.0", "4.0")
V2_MULTIPLES = (8, 16, 32, 64)


def get_v2_resolutions(aspect_ratio, megapixels):
    named = V2_RATIO_BY_BARE.get(aspect_ratio, aspect_ratio)
    if named not in V2_RATIOS or megapixels not in V2_MEGAPIXELS:
        raise ValueError("Unsupported aspect ratio or megapixels")
    aspect_ratio = named.split(" ", 1)[0]
    numerator, denominator = map(int, aspect_ratio.split(":"))
    ratio = numerator / denominator
    choices = []
    for scale in (0.9, 1.0, 1.1):
        pixels = float(megapixels) * 1000000 * scale
        for snap in (64, 32, 16, 8):
            width = max(64, int(math.sqrt(pixels * ratio) / snap + 0.5) * snap)
            height = max(64, int(math.sqrt(pixels / ratio) / snap + 0.5) * snap)
            if calculate_aspect_ratio(width, height) == aspect_ratio:
                label = f"{width}x{height} ({aspect_ratio})"
                if label not in choices:
                    choices.append(label)
                break
    return choices


class ResolutionSelectorV2(ResolutionSelector):
    DESCRIPTION = "Resolution Selector Plus: choose a discovered image model, named aspect ratio, megapixels and rounding multiple for up to four latent outputs."
    @classmethod
    def VALIDATE_INPUTS(cls, res1_aspect_ratio=None, res2_aspect_ratio=None,
                        res3_aspect_ratio=None, res4_aspect_ratio=None, batch_size=1):
        # ComfyUI skips the combo check for inputs named here, so v2.2.0 API
        # prompts with bare ratios ("16:9") validate. Other inputs keep the check.
        for ratio in (res1_aspect_ratio, res2_aspect_ratio, res3_aspect_ratio, res4_aspect_ratio):
            if ratio is not None and ratio not in V2_RATIOS and ratio not in V2_RATIO_BY_BARE:
                return f"Unsupported aspect ratio: {ratio!r}"
        if type(batch_size) is not int or not 1 <= batch_size <= 64:
            return "Batch size must be an integer from 1 to 64"
        return True

    @classmethod
    def INPUT_TYPES(cls):
        all_choices = list(dict.fromkeys(label for ratio in V2_RATIOS for mp in V2_MEGAPIXELS
                                         for label in get_v2_resolutions(ratio, mp)))
        required = {}
        optional = {}
        for slot in range(1, 5):
            target = required if slot == 1 else optional
            target[f"res{slot}_model"] = (list(V2_MODELS), {"default": "SDXL",
                "tooltip": "Discovered ComfyUI image model. Sets latent shape and the suggested rounding multiple; saved overrides remain.",
                "model_info": {label: {"channels": fmt[0], "downscale": fmt[1],
                                       "rank": fmt[2], "best_multiple": V2_MODELS[label][2]}
                               for label, fmt in V2_MODEL_FORMATS.items()}})
            target[f"res{slot}_aspect_ratio"] = (list(V2_RATIOS), {"default": "1:1 (Square)",
                                                  "tooltip": "Named aspect ratio, such as 16:9 (Widescreen)."})
            target[f"res{slot}_megapixels"] = (list(V2_MEGAPIXELS), {"default": "1.0",
                                                "tooltip": "Target image size in megapixels; selects nearby resolution candidates."})
            target[f"res{slot}_resolution"] = ((all_choices if slot == 1 else ["none"] + all_choices),
                                               {"default": get_v2_resolutions("1:1 (Square)", "1.0")[0] if slot == 1 else "none",
                                                "tooltip": "Select a resolution; later slots use none until activated."})
            target[f"res{slot}_multiple"] = (list(V2_MULTIPLES), {"default": V2_MODELS["SDXL"][2],
                                              "tooltip": "Pixel rounding step. Model selection suggests its best multiple; you may override it."})
        optional["batch_size"] = ("INT", {"default": 1, "min": 1, "max": 64,
                                          "display_name": "Batch size",
                                          "tooltip": "Number of latent samples in every slot batch."})
        return {"required": required, "optional": optional}

    RETURN_TYPES = ("INT", "INT", "LATENT") * 4
    RETURN_NAMES = tuple(f"res{slot}_{kind}" for slot in range(1, 5)
                         for kind in ("width", "height", "latent"))
    OUTPUT_TOOLTIPS = tuple(f"Resolution Selector Plus slot {slot} {kind}." for slot in range(1, 5)
                            for kind in ("width", "height", "latent"))
    FUNCTION = "select_resolutions"
    CATEGORY = "utils"

    def select_resolutions(self, res1_model, res1_aspect_ratio, res1_megapixels, res1_resolution, res1_multiple,
                           res2_model=None, res2_aspect_ratio="1:1", res2_megapixels="1.0", res2_resolution="none", res2_multiple=8,
                           res3_model=None, res3_aspect_ratio="1:1", res3_megapixels="1.0", res3_resolution="none", res3_multiple=8,
                           res4_model=None, res4_aspect_ratio="1:1", res4_megapixels="1.0", res4_resolution="none", res4_multiple=8,
                           batch_size=1):
        if type(batch_size) is not int or not 1 <= batch_size <= 64:
            raise ValueError("Batch size must be an integer from 1 to 64")
        slots = ((res1_model, res1_aspect_ratio, res1_megapixels, res1_resolution, res1_multiple),
                 (res2_model, res2_aspect_ratio, res2_megapixels, res2_resolution, res2_multiple),
                 (res3_model, res3_aspect_ratio, res3_megapixels, res3_resolution, res3_multiple),
                 (res4_model, res4_aspect_ratio, res4_megapixels, res4_resolution, res4_multiple))
        result = []
        inactive = False
        warned = False
        for model, ratio, mp, label, multiple in slots:
            if label == "none":
                inactive = True
                result.extend((0, 0, None))
                continue
            if inactive or label not in get_v2_resolutions(ratio, mp):
                raise ValueError("Resolution does not match its slot or a previous slot is inactive")
            model = model or "SDXL"
            if multiple not in V2_MULTIPLES or model not in V2_MODELS:
                raise ValueError("Unsupported multiple or model")
            channels, downscale, rank = V2_MODEL_FORMATS[model]
            if multiple < downscale and not warned:
                print(f"Resolution Selector Plus: multiple {multiple} below latent downscale {downscale}; latent size floors")
                warned = True
            width, height = parse_resolution_string(label)
            width = max(multiple, ((width + multiple // 2) // multiple) * multiple)
            height = max(multiple, ((height + multiple // 2) // multiple) * multiple)
            shape = [batch_size, channels, height // downscale, width // downscale]
            if rank == 5:
                shape.insert(2, 1)
            kwargs = {"device": self.device}
            if model == "SD3" and COMFY_AVAILABLE:
                kwargs["dtype"] = comfy.model_management.intermediate_dtype()
            latent = {"samples": torch.zeros(shape, **kwargs), "downscale_ratio_spacial": downscale}
            result.extend((width, height, latent))
        return tuple(result)


# node_id must be unique: ComfyUI core ships a built-in "ResolutionSelector"
# (comfy_extras/nodes_resolution.py), so this pack registers under a distinct id.
NODE_CLASS_MAPPINGS = {
    "ResolutionSelectorPlus": ResolutionSelector,
    "ResolutionSelectorPlusV2": ResolutionSelectorV2,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ResolutionSelectorPlus": "Resolution Selector Plus (Legacy)",
    "ResolutionSelectorPlusV2": "Resolution Selector Plus",
}


# -- V3 node (import-guarded comfy_api schema) ---------------------------------
# Thin adapter: execute delegates to the V1 class so the logic is never forked.

try:
    from comfy_api.v0_0_2 import io, ComfyExtension

    class ResolutionSelectorPlusV3(io.ComfyNode):
        @classmethod
        def define_schema(cls) -> io.Schema:
            model_list, model_settings = ResolutionSelector.INPUT_TYPES()["required"]["model"]
            model_info = model_settings.get("model_info")
            all_resolutions = get_all_resolutions()
            mult = ["1x", "2x", "3x", "4x"]
            return io.Schema(
                node_id="ResolutionSelectorPlus",
                display_name="Resolution Selector Plus (Legacy)",
                is_deprecated=True,
                category="utils",
                description=ResolutionSelector.DESCRIPTION,
                inputs=[
                    io.Combo.Input("model", options=model_list, default="SDXL", tooltip=TIP_MODEL,
                                   extra_dict={"model_info": model_info} if model_info else None),
                    io.Combo.Input("resolution", options=all_resolutions,
                                   default=format_resolution(1024, 1024), tooltip=TIP_RESOLUTION),
                    io.Combo.Input("resolution_multiplier", options=mult, default="1x", tooltip=TIP_MULT),
                    io.Int.Input("batch_size", default=1, min=1, max=64, step=1, tooltip=TIP_BATCH),
                    io.Int.Input("custom_width", default=0, min=0, max=4096, step=8, optional=True, tooltip=TIP_CW),
                    io.Int.Input("custom_height", default=0, min=0, max=4096, step=8, optional=True, tooltip=TIP_CH),
                    io.Combo.Input("custom_multiplier", options=mult, default="1x", optional=True, tooltip=TIP_CMULT),
                    io.Int.Input("custom_batch", default=1, min=1, max=64, step=1, optional=True, tooltip=TIP_CBATCH),
                ],
                outputs=[
                    io.Int.Output(id="width", display_name="width", tooltip=OUTPUT_TIPS["width"]),
                    io.Int.Output(id="height", display_name="height", tooltip=OUTPUT_TIPS["height"]),
                    io.Latent.Output(id="latent", display_name="latent", tooltip=OUTPUT_TIPS["latent"]),
                    io.Int.Output(id="custom_width", display_name="custom_width", tooltip=OUTPUT_TIPS["custom_width"]),
                    io.Int.Output(id="custom_height", display_name="custom_height", tooltip=OUTPUT_TIPS["custom_height"]),
                    io.Latent.Output(id="custom_latent", display_name="custom_latent", tooltip=OUTPUT_TIPS["custom_latent"]),
                ],
            )

        @classmethod
        def execute(cls, model, resolution, resolution_multiplier="1x", batch_size=1,
                    custom_width=0, custom_height=0, custom_multiplier="1x", custom_batch=1) -> io.NodeOutput:
            result = ResolutionSelector().select_resolution(
                model, resolution, resolution_multiplier, batch_size,
                custom_width, custom_height, custom_multiplier, custom_batch)
            return io.NodeOutput(*result)

    class ResolutionSelectorPlusV2V3(io.ComfyNode):
        @classmethod
        def define_schema(cls) -> io.Schema:
            source = ResolutionSelectorV2.INPUT_TYPES()
            inputs = []
            for group in ("required", "optional"):
                for name, (choices, settings) in source[group].items():
                    if choices == "INT":
                        inputs.append(io.Int.Input(name, default=settings["default"],
                                                   min=settings["min"], max=settings["max"],
                                                   display_name=settings["display_name"],
                                                   tooltip=settings["tooltip"], optional=True))
                    else:
                        inputs.append(io.Combo.Input(name, options=choices, default=settings["default"],
                                                     display_name=name.replace("_", " ").replace("res", "Res ", 1),
                                                     tooltip=settings.get("tooltip"),
                                                     optional=group == "optional",
                                                     extra_dict={"model_info": settings["model_info"]} if "model_info" in settings else None))
            outputs = []
            for name, kind, tooltip in zip(ResolutionSelectorV2.RETURN_NAMES,
                                           ResolutionSelectorV2.RETURN_TYPES,
                                           ResolutionSelectorV2.OUTPUT_TOOLTIPS):
                output = io.Latent.Output if kind == "LATENT" else io.Int.Output
                outputs.append(output(id=name, display_name=name, tooltip=tooltip))
            return io.Schema(node_id="ResolutionSelectorPlusV2", display_name="Resolution Selector Plus",
                             description=ResolutionSelectorV2.DESCRIPTION,
                             category="utils", inputs=inputs, outputs=outputs)

        @classmethod
        def validate_inputs(cls, res1_aspect_ratio=None, res2_aspect_ratio=None,
                            res3_aspect_ratio=None, res4_aspect_ratio=None, batch_size=1):
            return ResolutionSelectorV2.VALIDATE_INPUTS(
                res1_aspect_ratio, res2_aspect_ratio, res3_aspect_ratio, res4_aspect_ratio, batch_size)

        @classmethod
        def execute(cls, res1_model, res1_aspect_ratio, res1_megapixels, res1_resolution, res1_multiple,
                    **optional) -> io.NodeOutput:
            return io.NodeOutput(*ResolutionSelectorV2().select_resolutions(
                res1_model, res1_aspect_ratio, res1_megapixels, res1_resolution, res1_multiple, **optional))

    class ResolutionSelectorPlusExtension(ComfyExtension):
        async def get_node_list(self):
            return [ResolutionSelectorPlusV3, ResolutionSelectorPlusV2V3]

    async def comfy_entrypoint() -> "ResolutionSelectorPlusExtension":
        return ResolutionSelectorPlusExtension()

except ImportError:
    # Older ComfyUI without comfy_api: V1 mappings above are the only path.
    pass
