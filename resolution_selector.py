import torch

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
        "portrait": [(680, 2048), (928, 1664), (1024, 1536), (1024, 2048), (1056, 1584), (1080, 1920), (1104, 1472), (1140, 1472), (1152, 2048), (1200, 1800), (1368, 2048), (1464, 2048), (1536, 2048), (1608, 2048), (1640, 2048), (1704, 2048)],
        "landscape": [(1280, 720), (1472, 1104), (1472, 1140), (1536, 1024), (1584, 1056), (1664, 928), (1800, 1200), (1920, 1080), (2048, 680), (2048, 1024), (2048, 1152), (2048, 1368), (2048, 1464), (2048, 1536), (2048, 1608), (2048, 1640), (2048, 1704)],
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
        "portrait": [(512, 768), (512, 682), (512, 1024), (680, 2048), (768, 1024), (768, 1344), (1024, 2048), (1080, 1920), (1200, 1800), (1368, 2048), (1464, 2048), (1536, 2048), (1608, 2048), (1640, 2048), (1704, 2048)],
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
    Return the latent channel count for a model.

    SD 1.5 and SDXL use 4-channel latents. Flux, Qwen Image, and Z-Image use
    16-channel latents. A wrong channel count makes the LATENT output unusable
    with that model's sampler.

    For "All" (no specific model) this defaults to 4 for backward compatibility
    with SD-based workflows; pick the specific model to get a 16-channel latent.

    Args:
        model_name (str): Model name, or "All".

    Returns:
        int: Latent channel count (4 or 16).
    """
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


class ResolutionSelector:
    """
    Enhanced resolution selector supporting multiple image generation models.
    Provides model-specific resolution presets, custom dimension inputs, and empty latent output.
    """

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
        model_list = ["All"] + list(MODEL_RESOLUTIONS.keys())

        # Get all possible resolutions across all models (JavaScript will filter dynamically)
        all_resolutions = get_all_resolutions()

        return {
            "required": {
                "model": (model_list, {
                    "default": "SDXL"
                }),
                "resolution": (all_resolutions, {
                    "default": "1024x1024 (1:1 Square)"
                }),
                "resolution_multiplier": (["1x", "2x", "3x", "4x"], {
                    "default": "1x"
                }),
                "batch_size": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 64,
                    "step": 1,
                    "display": "number"
                }),
            },
            "optional": {
                "custom_width": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 4096,
                    "step": 8,
                    "display": "number"
                }),
                "custom_height": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 4096,
                    "step": 8,
                    "display": "number"
                }),
                "custom_multiplier": (["1x", "2x", "3x", "4x"], {
                    "default": "1x"
                }),
                "custom_batch": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 64,
                    "step": 1,
                    "display": "number"
                }),
            }
        }

    RETURN_TYPES = ("INT", "INT", "LATENT", "INT", "INT", "LATENT")
    RETURN_NAMES = ("width", "height", "latent", "custom_width", "custom_height", "custom_latent")
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

        # Apply multiplier to preset resolution
        width *= multiplier
        height *= multiplier

        # Channel count depends on the model (4 for SD1.5/SDXL, 16 for Flux/Qwen/Z-Image)
        channels = get_latent_channels(model)

        # Generate latent for preset resolution with batch size
        latent = self._generate_empty_latent(width, height, batch_size, channels)

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
            custom_latent = self._generate_empty_latent(final_custom_width, final_custom_height, custom_batch, channels)

            return (width, height, latent, final_custom_width, final_custom_height, custom_latent)
        else:
            # No custom dimensions: return zeros and a minimal VALID latent (8x8 -> 1x1
            # in latent space), never a zero-size [B,C,0,0] tensor.
            custom_latent = self._generate_empty_latent(8, 8, 1, channels)

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
        if model in MODEL_RESOLUTIONS:
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


NODE_CLASS_MAPPINGS = {
    "ResolutionSelector": ResolutionSelector,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ResolutionSelector": "Resolution Selector Plus",
}
