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
    def test_named_ratio_order_and_bare_compatibility(self):
        from nodes import V2_RATIOS
        test_resolution_selector.MockTorch.zeros = staticmethod(lambda shape, **kwargs: tuple(shape))
        expected = ['1:1 (Square)', '5:4 (Large Format)', '4:3 (Standard)',
                    '3:4 (Portrait Standard)', '3:2 (Photo)', '2:3 (Portrait Photo)',
                    '16:10 (Widescreen Monitor)', '5:8 (Portrait Widescreen Monitor)',
                    '16:9 (Widescreen)', '9:16 (Portrait Widescreen)',
                    '2:1 (Univisium)', '1:2 (Portrait Univisium)',
                    '21:9 (Ultrawide)', '12:5 (Cinemascope)',
                    '5:12 (Portrait Cinemascope)', '3:1 (Panorama)',
                    '1:3 (Portrait Panorama)']
        self.assertEqual(list(V2_RATIOS), expected)
        self.assertEqual(ResolutionSelectorV2.INPUT_TYPES()['required']['res1_aspect_ratio'][1]['default'], expected[0])
        for named in expected:
            bare = named.split(' ')[0]
            self.assertEqual(get_v2_resolutions(named, '1.0'), get_v2_resolutions(bare, '1.0'))
            label = get_v2_resolutions(named, '1.0')[0]
            self.assertEqual(ResolutionSelectorV2().select_resolutions('SDXL', bare, '1.0', label, 8)[:2],
                             ResolutionSelectorV2().select_resolutions('SDXL', named, '1.0', label, 8)[:2])

    def test_user_facing_names_and_tooltips(self):
        from nodes import NODE_DISPLAY_NAME_MAPPINGS, ResolutionSelector, OUTPUT_TIPS
        self.assertEqual(NODE_DISPLAY_NAME_MAPPINGS['ResolutionSelectorPlusV2'], 'Resolution Selector Plus')
        self.assertEqual(NODE_DISPLAY_NAME_MAPPINGS['ResolutionSelectorPlus'], 'Resolution Selector Plus (Legacy)')
        strings = [*OUTPUT_TIPS.values()]
        for cls in (ResolutionSelector, ResolutionSelectorV2):
            self.assertTrue(cls.DESCRIPTION)
            strings.append(cls.DESCRIPTION)
            strings.extend(cls.OUTPUT_TOOLTIPS)
            for group in cls.INPUT_TYPES().values():
                strings.extend(settings['tooltip'] for _, settings in group.values() if 'tooltip' in settings)
        for value in strings:
            self.assertNotRegex(value, r'(?i)v2|(?<![\w:])\d+:\d+(?! \()')

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
        self.assertEqual(list(inputs['optional'])[-1], 'batch_size')
        self.assertEqual(inputs['optional']['batch_size'], ('INT', {
            'default': 1, 'min': 1, 'max': 64, 'display_name': 'Batch size',
            'tooltip': 'Number of latent samples in every slot batch.'}))
        self.assertEqual(len(ResolutionSelectorV2.RETURN_TYPES), 12)
        self.assertEqual(inputs["required"]["res1_megapixels"][1]["default"], "1.0")
        for ratio in inputs["required"]["res1_aspect_ratio"][0]:
            for mp in inputs["required"]["res1_megapixels"][0]:
                labels = get_v2_resolutions(ratio, mp)
                self.assertTrue(labels)
                self.assertLessEqual(len(labels), 3)
                self.assertEqual(len(labels), len(set(labels)))
                for label in labels:
                    self.assertEqual(calculate_aspect_ratio(*parse_resolution_string(label)), ratio.split(' ')[0])
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

    def test_shared_batch_size_for_4d_and_5d_slots(self):
        test_resolution_selector.MockTorch.zeros = staticmethod(lambda shape, **kwargs: tuple(shape))
        label = get_v2_resolutions('1:1', '1.0')[0]
        for model in ('SDXL', 'Qwen-Image'):
            with self.subTest(model=model):
                result = ResolutionSelectorV2().select_resolutions(
                    model, '1:1', '1.0', label, 8,
                    res2_model=model, res3_model=model, res4_model=model,
                    res2_resolution=label, res3_resolution=label, res4_resolution=label,
                    batch_size=3)
                for slot in range(4):
                    self.assertEqual(result[slot * 3 + 2]['samples'][0], 3)
                self.assertEqual(len(result[2]['samples']), 5 if model == 'Qwen-Image' else 4)
                self.assertEqual(result[0:2], result[3:5])
                self.assertEqual(ResolutionSelectorV2().select_resolutions(
                    model, '1:1', '1.0', label, 8)[2]['samples'][0], 1)
        for size in (0, 65):
            with self.assertRaises(ValueError):
                ResolutionSelectorV2().select_resolutions('SDXL', '1:1', '1.0', label, 8,
                                                         batch_size=size)

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
        from model_discovery import discover_models, snapshot_classes
        expected = ['SD 1.5', 'SDXL', 'SD3', 'Flux.1', 'Flux.2', 'Chroma', 'Z-Image',
                    'Qwen-Image', 'Qwen-Image 2.1', 'HiDream', 'HunyuanImage 2.1', 'Other (4ch /8)']
        self.assertEqual(list(V2_MODELS)[:11], expected[:11])
        self.assertEqual(list(V2_MODELS)[-1], expected[-1])
        self.assertEqual(V2_MODELS, discover_models(snapshot_classes()))
        expected_formats = [(4, 8, 4), (4, 8, 4), (16, 8, 4), (16, 8, 4),
                            (128, 16, 4), (16, 8, 4), (16, 8, 4), (16, 8, 5),
                            (64, 16, 4), (16, 8, 4), (64, 32, 4), (4, 8, 4)]
        self.assertEqual([V2_MODELS[label][1] for label in expected], expected_formats)
        classes = {}
        for class_name, (channels, downscale, rank), _ in V2_MODELS.values():
            classes[class_name] = type(class_name, (), {'latent_channels': channels,
                'spacial_downscale_ratio': downscale, 'latent_dimensions': rank - 2})
        fake = types.ModuleType('comfy.latent_formats')
        fake.__dict__.update(classes)
        with patch.dict(sys.modules, {'comfy.latent_formats': fake}), patch.object(sys.modules['comfy'], 'latent_formats', fake, create=True):
            self.assertEqual([load_v2_model_formats()[label] for label in expected], expected_formats)
            fake.SDXL.latent_channels = 7
            self.assertEqual(load_v2_model_formats()['SDXL'], (7, 8, 4))

    def test_discovery_filters_and_unknown_class(self):
        from model_discovery import discover_models, snapshot_classes
        classes = snapshot_classes()
        latent = type('FutureFormat', (), {'latent_channels': 6,
            'spacial_downscale_ratio': 16, 'latent_dimensions': 2})
        future = type('FutureImage', (), {'latent_format': latent})
        alias = type('SD15', (), {'latent_format': classes[3].latent_format})
        fake = types.ModuleType('comfy.supported_models')
        fake.models = [*classes, future, alias]
        with patch.dict(sys.modules, {'comfy.supported_models': fake}):
            result = discover_models()
        self.assertEqual(result['FutureImage'], ('FutureFormat', (6, 16, 4), 16))
        for ratio, best in ((1, 8), (4, 8), (8, 8), (12, 16), (32, 32), (128, 64)):
            pixel = type('Fmt', (), {'latent_channels': 3, 'spacial_downscale_ratio': ratio,
                                     'latent_dimensions': 2})
            odd = type('FuturePixel', (), {'latent_format': pixel})
            self.assertEqual(discover_models([odd])['FuturePixel'][2], best, ratio)
        self.assertEqual(list(result).count('SD 1.5'), 1)
        self.assertNotIn('LotusD', result)
        self.assertNotIn('TripoSplat', result)
        self.assertIn('Ming-Image', result)
        self.assertIn('Anima', result)
        self.assertLess(list(result).index('FutureImage'), list(result).index('Other (4ch /8)'))

    def test_curated_labels_backfill_from_snapshot(self):
        from model_discovery import FRIENDLY, RELEASED, discover_models, snapshot_classes
        classes = [cls for cls in snapshot_classes() if cls.__name__ not in ('Flux3', 'Krea2', 'Flux2')]
        result = discover_models(classes)
        for label in ('Flux.3', 'Krea 2', 'Flux.2'):
            self.assertIn(label, result)
        self.assertEqual(result, discover_models(snapshot_classes()))
        for label in (*(l for l, _ in RELEASED.values()), *FRIENDLY.values()):
            self.assertIn(label, result)

    def test_snapshot_not_read_when_live_models_are_complete(self):
        import model_discovery
        classes = model_discovery.snapshot_classes()
        with patch.object(model_discovery, 'snapshot_classes', side_effect=AssertionError('read')):
            model_discovery.discover_models(classes)

    def test_researched_labels_multiples_and_aliases(self):
        from model_discovery import BEST_MULTIPLES, FRIENDLY, discover_models, snapshot_classes
        models = discover_models(snapshot_classes())
        self.assertEqual(len(models), 42)
        self.assertNotIn('PiD', models)
        for name, label in FRIENDLY.items():
            self.assertIn(label, models, name)
        for label in ('Hunyuan-DiT', 'KOALA'):
            self.assertEqual(list(models).count(label), 1)
        for label, best in (('Krea 2', 16), ('HiDream-O1', 32),
                            ('Lumina Image 2.0', 16), ('KOALA', 8)):
            self.assertEqual(models[label][2], best)
        self.assertEqual(models['Qwen-Image 2.1'][2], BEST_MULTIPLES['QwenImage21'])

    def test_legacy_new_models_use_all_and_model_latents(self):
        from nodes import ResolutionSelector, get_all_resolutions, format_resolution
        test_resolution_selector.MockTorch.zeros = staticmethod(lambda shape, **kwargs: tuple(shape))
        models = ResolutionSelector.INPUT_TYPES()['required']['model'][0]
        self.assertEqual(models, ['All'] + ResolutionSelectorV2.INPUT_TYPES()['required']['res1_model'][0])
        self.assertIn('HunyuanImage 2.1', models)
        label = format_resolution(1024, 1024)
        self.assertIn(label, get_all_resolutions())
        result = ResolutionSelector().select_resolution('HunyuanImage 2.1', label)
        self.assertEqual(result[2]['samples'], (1, 64, 32, 32))
        flux2 = ResolutionSelector().select_resolution('Flux.2', label)
        self.assertEqual(flux2[2]['samples'], (1, 128, 64, 64))
        qwen = ResolutionSelector().select_resolution('JoyImage', label)
        self.assertEqual(qwen[2]['samples'], (1, 16, 1, 128, 128))
        with self.assertRaises(ValueError):
            ResolutionSelector().select_resolution('HunyuanImage 2.1', format_resolution(1000, 1000))

    def test_validate_inputs_accepts_bare_and_named_ratios(self):
        import inspect
        spec = inspect.getfullargspec(ResolutionSelectorV2.VALIDATE_INPUTS)
        self.assertIsNone(spec.varkw)  # **kwargs would skip the combo check for every input
        self.assertEqual([n for n in spec.args if n != 'cls'],
                         [f'res{slot}_aspect_ratio' for slot in range(1, 5)] + ['batch_size'])
        validate = ResolutionSelectorV2.VALIDATE_INPUTS
        self.assertIs(validate(res1_aspect_ratio='16:9'), True)
        self.assertIs(validate(res1_aspect_ratio='16:9 (Widescreen)', res3_aspect_ratio='1:3'), True)
        self.assertIs(validate(), True)
        self.assertIsInstance(validate(res2_aspect_ratio='7:5'), str)
        self.assertIsInstance(validate(res1_aspect_ratio='16:9 (Wrong)'), str)
        self.assertIs(validate(batch_size=64), True)
        self.assertIsInstance(validate(batch_size=0), str)

    def test_legacy_lists_only_presets_valid_for_discovered_models(self):
        from nodes import ResolutionSelector, V2_MODELS, LEGACY_EQUIVALENTS, get_resolution_list, get_all_resolutions
        test_resolution_selector.MockTorch.zeros = staticmethod(lambda shape, **kwargs: tuple(shape))
        info = ResolutionSelector.INPUT_TYPES()['required']['model'][1]['model_info']
        for model, (_, _, best) in V2_MODELS.items():
            if model in LEGACY_EQUIVALENTS or model == 'Other (4ch /8)':
                continue
            self.assertEqual(info[model]['best_multiple'], best)
            listed = get_resolution_list(model)
            self.assertTrue(listed, model)
            self.assertLessEqual(len(listed), len(get_all_resolutions()))
            for label in listed:
                ResolutionSelector().select_resolution(model, label)
        self.assertLessEqual(len(get_resolution_list('HunyuanImage 2.1')), 17)

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
        self.assertEqual(schema.display_name, 'Resolution Selector Plus')
        self.assertEqual(schema.description, module.ResolutionSelectorV2.DESCRIPTION)
        self.assertEqual([item.id for item in schema.outputs], list(module.ResolutionSelectorV2.RETURN_NAMES))
        self.assertEqual([item.display_name for item in schema.outputs[:3]],
                         ['res1_width', 'res1_height', 'res1_latent'])
        self.assertEqual([item.name for item in schema.inputs],
                         list(module.ResolutionSelectorV2.INPUT_TYPES()['required']) +
                         list(module.ResolutionSelectorV2.INPUT_TYPES()['optional']))
        self.assertEqual(schema.inputs[-1].name, 'batch_size')
        self.assertEqual(schema.inputs[-1].display_name, 'Batch size')
        self.assertEqual(schema.inputs[-1].default, 1)
        self.assertEqual([item.display_name for item in schema.inputs[:5]],
                         ['Res 1 model', 'Res 1 aspect ratio', 'Res 1 megapixels', 'Res 1 resolution', 'Res 1 multiple'])
        old = module.ResolutionSelectorPlusV3.define_schema()
        self.assertEqual(old.display_name, 'Resolution Selector Plus (Legacy)')
        self.assertEqual(old.description, module.ResolutionSelector.DESCRIPTION)
        for node_schema in (schema, old):
            for item in (*node_schema.inputs, *node_schema.outputs):
                if getattr(item, 'tooltip', None):
                    self.assertNotRegex(item.tooltip, r'(?i)v2|(?<![\w:])\d+:\d+(?! \()')
        resolution = next(item for item in old.inputs if item.name == 'resolution')
        self.assertIn(resolution.default, resolution.options)
        self.assertTrue(module.ResolutionSelectorPlusV3.define_schema().is_deprecated)
        self.assertEqual(module.ResolutionSelector.RETURN_TYPES, ('INT', 'INT', 'LATENT') * 2)
        self.assertIs(module.NODE_CLASS_MAPPINGS['ResolutionSelectorPlus'], module.ResolutionSelector)
        self.assertIs(module.NODE_CLASS_MAPPINGS['ResolutionSelectorPlusV2'], module.ResolutionSelectorV2)
        label = module.get_v2_resolutions('1:1', '1.0')[0]
        self.assertEqual(module.ResolutionSelectorPlusV2V3.execute(
            'SDXL', '1:1', '1.0', label, 8, batch_size=3)[2]['samples'][0], 3)
        self.assertEqual(module.ResolutionSelectorPlusV2V3.execute(
            'SDXL', '1:1', '1.0', label, 8)[2]['samples'][0], 1)
        self.assertIsInstance(module.ResolutionSelectorPlusV2V3.validate_inputs(batch_size=0), str)




class TestPackageImport(unittest.TestCase):
    def test_imports_as_a_package_like_comfyui(self):
        # ComfyUI loads custom nodes as packages; plain-module imports inside them fail there.
        import os
        root = os.path.dirname(os.path.abspath(__file__))
        spec = importlib.util.spec_from_file_location(
            'rsp_pkg_under_test', os.path.join(root, '__init__.py'), submodule_search_locations=[root])
        package = importlib.util.module_from_spec(spec)
        sys.modules['rsp_pkg_under_test'] = package
        saved_path = list(sys.path)
        sys.path[:] = [p for p in sys.path if os.path.abspath(p or '.') != root]
        try:
            spec.loader.exec_module(package)
        finally:
            sys.path[:] = saved_path
            for name in [n for n in sys.modules if n.startswith('rsp_pkg_under_test')]:
                del sys.modules[name]
        self.assertIn('ResolutionSelectorPlusV2', package.NODE_CLASS_MAPPINGS)


if __name__ == '__main__':
    unittest.main()
