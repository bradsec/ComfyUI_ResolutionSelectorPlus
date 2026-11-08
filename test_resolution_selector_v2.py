import unittest
import json
import subprocess
import importlib.util
import sys
import types
from unittest.mock import patch

import test_resolution_selector  # Install the existing lightweight torch stub.
from nodes import ResolutionSelectorV2, calculate_aspect_ratio, get_v2_resolutions, parse_resolution_string


class TestResolutionSelectorV2(unittest.TestCase):
    def test_legacy_default_is_listed(self):
        from nodes import ResolutionSelector
        choices, settings = ResolutionSelector.INPUT_TYPES()['required']['resolution']
        self.assertIn(settings['default'], choices)

    def test_schema_and_candidates(self):
        inputs = ResolutionSelectorV2.INPUT_TYPES()
        self.assertNotIn("model", inputs["required"])
        self.assertNotIn("multiple", inputs["required"])
        self.assertEqual(inputs['required']['res1_model'][1]['default'], 'SDXL')
        for slot in range(1, 5):
            group = inputs["required" if slot == 1 else "optional"]
            start = 0 if slot == 1 else (slot - 2) * 5
            self.assertEqual(list(group)[start:start + 5],
                             [f"res{slot}_{name}" for name in ("model", "aspect_ratio", "megapixels", "resolution", "multiple")])
        self.assertEqual(len(ResolutionSelectorV2.RETURN_TYPES), 12)
        self.assertEqual(inputs["required"]["res1_megapixels"][1]["default"], "1.0")
        for ratio in inputs["required"]["res1_aspect_ratio"][0]:
            for mp in inputs["required"]["res1_megapixels"][0]:
                labels = get_v2_resolutions(ratio, mp)
                self.assertTrue(labels)
                self.assertLessEqual(len(labels), 3)
                self.assertEqual(len(labels), len(set(labels)))
                for label in labels:
                    self.assertEqual(calculate_aspect_ratio(*parse_resolution_string(label)), ratio)
                self.assertTrue(set(labels) <= set(inputs["required"]["res1_resolution"][0]))
        for ratio, mp in (("21:9", "1.0"), ("16:9", "0.5")):
            with self.subTest(ratio=ratio, megapixels=mp):
                self.assertTrue(all(label.endswith(f"({ratio})") for label in get_v2_resolutions(ratio, mp)))
                self.assertTrue(all("  " not in label for label in get_v2_resolutions(ratio, mp)))
        for label in get_v2_resolutions("16:9", "1.0"):
            width, height = parse_resolution_string(label)
            self.assertAlmostEqual(width / height, 16 / 9, delta=0.15)
            self.assertTrue(800000 <= width * height <= 1200000)

    def test_execution_and_validation(self):
        from nodes import V2_MODELS
        test_resolution_selector.MockTorch.zeros = staticmethod(lambda shape, **kwargs: tuple(shape))
        node = ResolutionSelectorV2()
        label = get_v2_resolutions("16:9", "1.0")[0]
        base_width, base_height = parse_resolution_string(label)
        result = node.select_resolutions('Flux.1', "16:9", "1.0", label, 64)
        self.assertEqual(result[0], max(64, ((base_width + 32) // 64) * 64))
        self.assertEqual(result[2]["samples"], (1, 16, result[1] // 8, result[0] // 8))
        self.assertEqual(result[3:], (0, 0, None) * 3)
        with self.assertRaises(ValueError):
            node.select_resolutions('SDXL', "1:1", "1.0", label, 8)
        with self.assertRaises(ValueError):
            node.select_resolutions('SDXL', "16:9", "1.0", label, 8, res3_resolution=label)

    def test_python_browser_candidate_parity(self):
        from nodes import V2_RATIOS, V2_MEGAPIXELS
        script = "import {RATIOS, MEGAPIXELS, getResolutions} from './js/resolution_selector_v2_core.js'; console.log(JSON.stringify(RATIOS.flatMap(r => MEGAPIXELS.map(m => getResolutions(r,m)))))"
        actual = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', script], text=True))
        expected = [get_v2_resolutions(ratio, mp) for ratio in V2_RATIOS for mp in V2_MEGAPIXELS]
        self.assertEqual(actual, expected)

    def test_all_slots_and_latent_shapes(self):
        from nodes import V2_MODELS, V2_MODEL_FORMATS
        test_resolution_selector.MockTorch.zeros = staticmethod(lambda shape, **kwargs: tuple(shape))
        label = get_v2_resolutions('1:1', '1.0')[0]
        for model in V2_MODELS:
            channels, downscale, rank = V2_MODEL_FORMATS[model]
            result = ResolutionSelectorV2().select_resolutions(
                model, '1:1', '1.0', label, 32,
                res2_model=model, res3_model=model, res4_model=model,
                res2_resolution=label, res3_resolution=label, res4_resolution=label)
            self.assertEqual(len(result), 12)
            for slot in range(4):
                width, height, latent = result[slot * 3:slot * 3 + 3]
                expected = (1, channels, height // downscale, width // downscale)
                if rank == 5:
                    expected = expected[:2] + (1,) + expected[2:]
                self.assertEqual(latent['samples'], expected)
                self.assertEqual(latent['downscale_ratio_spacial'], downscale)

    def test_slots_use_independent_models_and_multiples(self):
        test_resolution_selector.MockTorch.zeros = staticmethod(lambda shape, **kwargs: tuple(shape))
        label = get_v2_resolutions('1:1', '1.0')[0]
        base_width, _ = parse_resolution_string(label)
        sd = 'SDXL'
        flux = 'Flux.2'
        result = ResolutionSelectorV2().select_resolutions(
            sd, '1:1', '1.0', label, 8,
            res2_model=flux, res2_resolution=label, res2_multiple=64)
        self.assertEqual(result[0], max(8, ((base_width + 4) // 8) * 8))
        self.assertEqual(result[3], max(64, ((base_width + 32) // 64) * 64))
        self.assertEqual(result[2]['samples'], (1, 4, result[1] // 8, result[0] // 8))
        self.assertEqual(result[5]['samples'], (1, 128, result[4] // 16, result[3] // 16))
        self.assertEqual(result[2]['downscale_ratio_spacial'], 8)
        self.assertEqual(result[5]['downscale_ratio_spacial'], 16)

    def test_model_fallback_matches_runtime_format(self):
        from nodes import V2_MODELS, load_v2_model_formats
        expected = ['SD 1.5', 'SDXL', 'SD3', 'Flux.1', 'Flux.2', 'Chroma', 'Z-Image',
                    'Qwen-Image', 'Qwen-Image 2.1', 'HiDream', 'HunyuanImage 2.1', 'Other (4ch /8)']
        self.assertEqual(list(V2_MODELS), expected)
        expected_formats = [(4, 8, 4), (4, 8, 4), (16, 8, 4), (16, 8, 4),
                            (128, 16, 4), (16, 8, 4), (16, 8, 4), (16, 8, 5),
                            (64, 16, 4), (16, 8, 4), (64, 32, 4), (4, 8, 4)]
        self.assertEqual([entry[1] for entry in V2_MODELS.values()], expected_formats)
        script = "import {BEST_MULTIPLES} from './js/resolution_selector_v2_core.js'; console.log(JSON.stringify(BEST_MULTIPLES))"
        js_multiples = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', script], text=True))
        self.assertEqual(js_multiples, {model: best for model, (_, _, best) in V2_MODELS.items()})
        classes = {}
        for class_name, (channels, downscale, rank), _ in V2_MODELS.values():
            classes[class_name] = type(class_name, (), {'latent_channels': channels,
                'spacial_downscale_ratio': downscale, 'latent_dimensions': rank - 2})
        fake = types.ModuleType('comfy.latent_formats')
        fake.__dict__.update(classes)
        with patch.dict(sys.modules, {'comfy.latent_formats': fake}), patch.object(sys.modules['comfy'], 'latent_formats', fake, create=True):
            self.assertEqual(list(load_v2_model_formats().values()), expected_formats)
            fake.SDXL.latent_channels = 7
            self.assertEqual(load_v2_model_formats()['SDXL'], (7, 8, 4))

    def test_v3_registration_matches_v1(self):
        class Port:
            @staticmethod
            def Input(name, **kwargs):
                return types.SimpleNamespace(name=name, **kwargs)

            @staticmethod
            def Output(**kwargs):
                return types.SimpleNamespace(**kwargs)

        io = types.SimpleNamespace(ComfyNode=type('ComfyNode', (), {}),
                                   Schema=lambda **kwargs: types.SimpleNamespace(**kwargs),
                                   NodeOutput=lambda *args: args, Combo=Port, Int=Port, Latent=Port)
        fake = types.ModuleType('comfy_api.v0_0_2')
        fake.io = io
        fake.ComfyExtension = type('ComfyExtension', (), {})
        with patch.dict(sys.modules, {'comfy_api': types.ModuleType('comfy_api'), 'comfy_api.v0_0_2': fake}):
            spec = importlib.util.spec_from_file_location('nodes_v3_test', 'nodes.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        schema = module.ResolutionSelectorPlusV2V3.define_schema()
        self.assertEqual(schema.node_id, 'ResolutionSelectorPlusV2')
        self.assertEqual([item.id for item in schema.outputs], list(module.ResolutionSelectorV2.RETURN_NAMES))
        self.assertEqual([item.display_name for item in schema.outputs[:3]],
                         ['res1_width', 'res1_height', 'res1_latent'])
        self.assertEqual([item.name for item in schema.inputs],
                         list(module.ResolutionSelectorV2.INPUT_TYPES()['required']) +
                         list(module.ResolutionSelectorV2.INPUT_TYPES()['optional']))
        self.assertEqual([item.display_name for item in schema.inputs[:5]],
                         ['Res 1 model', 'Res 1 aspect ratio', 'Res 1 megapixels', 'Res 1 resolution', 'Res 1 multiple'])
        old = module.ResolutionSelectorPlusV3.define_schema()
        resolution = next(item for item in old.inputs if item.name == 'resolution')
        self.assertIn(resolution.default, resolution.options)
        self.assertTrue(module.ResolutionSelectorPlusV3.define_schema().is_deprecated)
        self.assertEqual(module.ResolutionSelector.RETURN_TYPES, ('INT', 'INT', 'LATENT') * 2)
        self.assertIs(module.NODE_CLASS_MAPPINGS['ResolutionSelectorPlus'], module.ResolutionSelector)
        self.assertIs(module.NODE_CLASS_MAPPINGS['ResolutionSelectorPlusV2'], module.ResolutionSelectorV2)


if __name__ == "__main__":
    unittest.main()
