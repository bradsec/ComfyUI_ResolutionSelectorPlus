#!/usr/bin/env python3
"""
Test script for ResolutionSelector enhancements
"""

import sys
import unittest
sys.path.insert(0, '.')

# Mock torch module for testing without ComfyUI environment
class MockTorch:
    class device:
        def __init__(self, name):
            self.name = name

sys.modules['torch'] = MockTorch()
sys.modules['comfy'] = type('module', (), {'model_management': None})()

from nodes import (
    calculate_aspect_ratio,
    format_resolution,
    get_resolution_list,
    get_all_resolutions,
    get_default_resolution,
    get_latent_channels,
    parse_resolution_string,
    MODEL_RESOLUTIONS
)

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
    assert result == "1920x1080 (16:9 Widescreen)"
    assert result.startswith("1920x1080"), f"Should start with resolution"

    result = format_resolution(1024, 1024)
    print(f"  1024x1024 → '{result}'")
    assert "(1:1 Square)" in result, f"Should contain aspect ratio and orientation"
    assert result.startswith("1024x1024"), f"Should start with resolution"

    result = format_resolution(1080, 1920)
    print(f"  1080x1920 → '{result}'")
    assert result == "1080x1920 (9:16 Portrait Widescreen)"
    assert result.startswith("1080x1920"), f"Should start with resolution"
    print("  ✓ Format resolution tests passed")

def test_parse_resolution():
    """Test resolution string parsing"""
    print("\nTesting resolution string parsing:")
    # Saved workflows may still contain padded labels.
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
    flux_res = get_resolution_list("Flux.1")
    print(f"  Flux.1 has {len(flux_res)} resolutions")
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
    expected = {"Flux": 16, "Flux.1": 16, "Qwen Image": 16, "Qwen-Image": 16, "Z-Image": 16, "SD 1.5": 4, "SDXL": 4, "All": 4}
    for model, channels in expected.items():
        got = get_latent_channels(model)
        assert got == channels, f"{model}: expected {channels} channels, got {got}"
    print(f"  ✓ Channel mapping correct: {expected}")


def test_qwen_official_resolutions():
    """Official Qwen-Image sizes must be present in all 16-channel models"""
    print("\nTesting official Qwen resolutions in 16-channel models:")
    want = [(1328, 1328), (1664, 928), (928, 1664), (1472, 1104),
            (1104, 1472), (1584, 1056), (1056, 1584)]
    for model in ["Flux.1", "Qwen-Image", "Z-Image"]:
        resolutions = get_resolution_list(model)
        for w, h in want:
            s = format_resolution(w, h)
            assert s in resolutions, f"{model} missing {w}x{h}"
    print(f"  ✓ All {len(want)} resolutions present in Flux, Qwen Image, Z-Image")


def test_presets_satisfy_constraints():
    """Every preset must satisfy its own model's divisibility/min/max, or the
    reported width/height will not match the generated latent dimensions."""
    print("\nTesting preset dimensions against model constraints:")
    for model, data in MODEL_RESOLUTIONS.items():
        c = data["constraints"]
        for category in ("square", "portrait", "landscape"):
            for w, h in data[category]:
                assert w % c["divisible_by"] == 0 and h % c["divisible_by"] == 0, \
                    f"{model} {w}x{h} not divisible by {c['divisible_by']}"
                assert c["min"] <= w <= c["max"] and c["min"] <= h <= c["max"], \
                    f"{model} {w}x{h} outside {c['min']}-{c['max']}"
    print("  ✓ All presets satisfy their model constraints")


def test_js_table_matches_python():
    """js/resolution_selector.js hand-mirrors MODEL_RESOLUTIONS; catch drift."""
    print("\nTesting JS resolution table matches Python:")
    import json, os, re
    js_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "js", "resolution_selector.js")
    with open(js_path, encoding="utf-8") as f:
        src = f.read()
    match = re.search(r"const MODEL_RESOLUTIONS = (\{.*?\n\});", src, re.DOTALL)
    assert match, "MODEL_RESOLUTIONS table not found in resolution_selector.js"
    js_table = json.loads(re.sub(r",(\s*[}\]])", r"\1", match.group(1)))
    py_table = {model: {cat: [list(p) for p in data[cat]]
                        for cat in ("square", "portrait", "landscape")}
                for model, data in MODEL_RESOLUTIONS.items()}
    assert js_table == py_table, "JS MODEL_RESOLUTIONS differs from nodes.py"
    print("  ✓ JS table in sync with nodes.py")


class TestResolutionSelector(unittest.TestCase):
    """unittest wrapper so `python -m unittest` discovers these tests (R5).

    Each method delegates to the existing function-style test; an assertion
    failure inside propagates and fails the unittest case.
    """

    def test_aspect_ratio(self):
        test_aspect_ratio()

    def test_format_resolution(self):
        test_format_resolution()

    def test_parse_resolution(self):
        test_parse_resolution()

    def test_model_resolutions(self):
        test_model_resolutions()

    def test_new_resolutions(self):
        test_new_resolutions()

    def test_all_resolutions_unique(self):
        test_all_resolutions_unique()

    def test_latent_channels(self):
        test_latent_channels()

    def test_qwen_official_resolutions(self):
        test_qwen_official_resolutions()

    def test_presets_satisfy_constraints(self):
        test_presets_satisfy_constraints()

    def test_js_table_matches_python(self):
        test_js_table_matches_python()

    def test_legacy_models_match_new_node(self):
        from nodes import ResolutionSelector, ResolutionSelectorV2
        self.assertEqual(ResolutionSelector.INPUT_TYPES()['required']['model'][0],
                         ['All'] + ResolutionSelectorV2.INPUT_TYPES()['required']['res1_model'][0])

    def test_generated_presets_and_defaults(self):
        from nodes import ResolutionSelector, V2_MODELS, V2_RATIOS
        node = ResolutionSelector()
        for model in ['All', *V2_MODELS]:
            labels = get_resolution_list(model)
            self.assertTrue(labels, model)
            self.assertIn(get_default_resolution(model), labels, model)
            for label in labels:
                self.assertIs(node.VALIDATE_INPUTS(model=model, resolution=label), True,
                              (model, label))
            if model != 'All' and model not in MODEL_RESOLUTIONS:
                self.assertEqual(len(labels), len(set(labels)))
                self.assertLessEqual(len(labels), len(V2_RATIOS))
                self.assertTrue(all(800000 <= w * h <= 1200000 for w, h in
                                    map(parse_resolution_string, labels)), model)

    def test_old_names_and_labels_run(self):
        from nodes import ResolutionSelector
        MockTorch.zeros = staticmethod(lambda shape, **kwargs: tuple(shape))
        node = ResolutionSelector()
        for old, new, label in (("Flux", "Flux.1", "1024x1024    (1:1 Square)"),
                                ("Qwen Image", "Qwen-Image", "1920x1080    (16:9 Landscape)")):
            self.assertIs(ResolutionSelector.VALIDATE_INPUTS(model=old, resolution=label), True)
            self.assertEqual(node.select_resolution(old, label), node.select_resolution(new, label))
        self.assertIs(ResolutionSelector.VALIDATE_INPUTS(model="SDXL", resolution="1024x1024    (1:1 Square)"), True)
        self.assertIs(ResolutionSelector.VALIDATE_INPUTS(model="SD3", resolution="2048x2048    (1:1 Square)"), True)
        self.assertNotEqual(ResolutionSelector.VALIDATE_INPUTS(model="Flux", resolution="1025x1024 (1:1 Square)"), True)

    def test_named_labels(self):
        self.assertEqual(format_resolution(1024, 768), "1024x768 (4:3 Standard)")
        self.assertEqual(format_resolution(768, 1024), "768x1024 (3:4 Portrait Standard)")
        self.assertEqual(format_resolution(1536, 1024), "1536x1024 (3:2 Photo)")
        self.assertEqual(format_resolution(1024, 1536), "1024x1536 (2:3 Portrait Photo)")


if __name__ == "__main__":
    print("=" * 60)
    print("ResolutionSelector Enhancement Tests")
    print("=" * 60)

    try:
        test_aspect_ratio()
        test_format_resolution()
        test_parse_resolution()
        test_model_resolutions()
        test_new_resolutions()
        test_all_resolutions_unique()
        test_latent_channels()
        test_qwen_official_resolutions()
        test_presets_satisfy_constraints()
        test_js_table_matches_python()

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
