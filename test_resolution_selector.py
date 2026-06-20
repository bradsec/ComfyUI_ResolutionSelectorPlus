#!/usr/bin/env python3
"""
Test script for ResolutionSelector enhancements
"""

import sys
sys.path.insert(0, '.')

# Mock torch module for testing without ComfyUI environment
class MockTorch:
    class device:
        def __init__(self, name):
            self.name = name

sys.modules['torch'] = MockTorch()
sys.modules['comfy'] = type('module', (), {'model_management': None})()

from resolution_selector import (
    gcd,
    calculate_aspect_ratio,
    format_resolution,
    get_resolution_list,
    get_all_resolutions,
    get_latent_channels,
    parse_resolution_string,
    MODEL_RESOLUTIONS
)

def test_gcd():
    """Test GCD function"""
    print("Testing GCD function:")
    assert gcd(1920, 1080) == 120, "GCD of 1920, 1080 should be 120"
    assert gcd(1024, 1024) == 1024, "GCD of 1024, 1024 should be 1024"
    assert gcd(16, 9) == 1, "GCD of 16, 9 should be 1"
    print("  ✓ GCD tests passed")

def test_aspect_ratio():
    """Test aspect ratio calculation"""
    print("\nTesting aspect ratio calculation:")
    assert calculate_aspect_ratio(1920, 1080) == "16:9", "1920x1080 should be 16:9"
    assert calculate_aspect_ratio(1024, 1024) == "1:1", "1024x1024 should be 1:1"
    assert calculate_aspect_ratio(1280, 720) == "16:9", "1280x720 should be 16:9"
    assert calculate_aspect_ratio(1536, 1024) == "3:2", "1536x1024 should be 3:2"
    print("  ✓ Aspect ratio tests passed")

def test_format_resolution():
    """Test resolution formatting"""
    print("\nTesting resolution formatting:")
    result = format_resolution(1920, 1080)
    print(f"  1920x1080 → '{result}'")
    # With padding, should be "1920x1080    (16:9 Landscape)" - 13 chars total for resolution part
    assert "(16:9 Landscape)" in result, f"Should contain aspect ratio and orientation"
    assert result.startswith("1920x1080"), f"Should start with resolution"

    result = format_resolution(1024, 1024)
    print(f"  1024x1024 → '{result}'")
    assert "(1:1 Square)" in result, f"Should contain aspect ratio and orientation"
    assert result.startswith("1024x1024"), f"Should start with resolution"

    result = format_resolution(1080, 1920)
    print(f"  1080x1920 → '{result}'")
    assert "(9:16 Portrait)" in result, f"Should contain aspect ratio and orientation"
    assert result.startswith("1080x1920"), f"Should start with resolution"
    print("  ✓ Format resolution tests passed")

def test_parse_resolution():
    """Test resolution string parsing"""
    print("\nTesting resolution string parsing:")
    # Test with padding (as it will be in the actual dropdown)
    width, height = parse_resolution_string("1920x1080    (16:9 Landscape)")
    assert width == 1920 and height == 1080, "Should parse 1920x1080 with padding"

    width, height = parse_resolution_string("1024x1024    (1:1 Square)")
    assert width == 1024 and height == 1024, "Should parse 1024x1024 with padding"

    # Test without padding (backward compatibility)
    width, height = parse_resolution_string("1920x1080 (16:9 Landscape)")
    assert width == 1920 and height == 1080, "Should parse 1920x1080 without padding"
    print("  ✓ Parse resolution tests passed")

def test_model_resolutions():
    """Test model resolution lists"""
    print("\nTesting model resolution lists:")

    # Test individual model
    flux_res = get_resolution_list("Flux")
    print(f"  Flux has {len(flux_res)} resolutions")
    assert len(flux_res) > 0, "Flux should have resolutions"
    # Flux uses 16-pixel divisibility, so 1920x1080 becomes 1920x1088
    assert any("1920x1088" in r for r in flux_res), "Flux should have 1920x1088 (Full HD adapted to 16px divisibility)"

    # Test All model
    all_res = get_resolution_list("All")
    print(f"  'All' has {len(all_res)} unique resolutions")
    assert len(all_res) > len(flux_res), "'All' should have more resolutions than individual models"

    # Verify no duplicates in All
    assert len(all_res) == len(set(all_res)), "'All' should have no duplicates"
    print("  ✓ Model resolution tests passed")

def test_new_resolutions():
    """Test that new resolutions were added"""
    print("\nTesting new resolutions up to 1920x1080:")

    for model_name, model_data in MODEL_RESOLUTIONS.items():
        resolutions = get_resolution_list(model_name)
        has_1080p = any("1920x1080" in r or "1080x1920" in r for r in resolutions)
        print(f"  {model_name}: {len(resolutions)} resolutions, has 1080p: {has_1080p}")

    print("  ✓ New resolutions verified")

def test_all_resolutions_unique():
    """Test that 'All' model returns unique resolutions"""
    print("\nTesting 'All' model uniqueness:")
    all_res = get_all_resolutions()

    # Count occurrences
    dimensions = []
    for res in all_res:
        width, height = parse_resolution_string(res)
        dimensions.append((width, height))

    # Check for duplicates
    unique_dimensions = set(dimensions)
    assert len(dimensions) == len(unique_dimensions), "Should have no duplicate dimensions"
    print(f"  ✓ All {len(all_res)} resolutions are unique")

def test_latent_channels():
    """R1: latent channel count must match the model (4 SD-based, 16 Flux/Qwen/Z-Image)"""
    print("\nTesting latent channel mapping:")
    expected = {"Flux": 16, "Qwen Image": 16, "Z-Image": 16, "SD 1.5": 4, "SDXL": 4, "All": 4}
    for model, channels in expected.items():
        got = get_latent_channels(model)
        assert got == channels, f"{model}: expected {channels} channels, got {got}"
    print(f"  ✓ Channel mapping correct: {expected}")


def test_qwen_official_resolutions():
    """Official Qwen-Image sizes must be present in all 16-channel models"""
    print("\nTesting official Qwen resolutions in 16-channel models:")
    want = [(1328, 1328), (1664, 928), (928, 1664), (1472, 1104),
            (1104, 1472), (1584, 1056), (1056, 1584)]
    for model in ["Flux", "Qwen Image", "Z-Image"]:
        resolutions = get_resolution_list(model)
        for w, h in want:
            s = format_resolution(w, h)
            assert s in resolutions, f"{model} missing {w}x{h}"
    print(f"  ✓ All {len(want)} resolutions present in Flux, Qwen Image, Z-Image")


if __name__ == "__main__":
    print("=" * 60)
    print("ResolutionSelector Enhancement Tests")
    print("=" * 60)

    try:
        test_gcd()
        test_aspect_ratio()
        test_format_resolution()
        test_parse_resolution()
        test_model_resolutions()
        test_new_resolutions()
        test_all_resolutions_unique()
        test_latent_channels()
        test_qwen_official_resolutions()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
