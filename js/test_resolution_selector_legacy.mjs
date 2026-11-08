import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { RATIOS, getResolutions } from './resolution_selector_v2_core.js';

const source = readFileSync(new URL('./resolution_selector.js', import.meta.url), 'utf8')
    .replace(/^import .*;\n/gm, '');
let extension;
const context = {
    app: { registerExtension(value) { extension = value; } }, RATIOS, getResolutions,
    setTimeout(callback) { callback(); }, console,
};
runInNewContext(source, context);

function node(model, resolution) {
    const widgets = [
        { name: 'model', value: model, options: {} },
        { name: 'resolution', value: resolution, options: { values: [] } },
    ];
    return {
        comfyClass: 'ResolutionSelectorPlus', widgets, size: [200, 200],
        constructor: { nodeData: { input: { required: { model: [[], { model_info: {
            'Flux.1': { best_multiple: 16 }, 'Qwen-Image': { best_multiple: 16 },
            SD3: { best_multiple: 16 }, 'HunyuanImage 2.1': { best_multiple: 32 },
            'Other (4ch /8)': { best_multiple: 8 },
        } }] } } } },
        setSize(size) { this.size = size; }, setDirtyCanvas() {},
    };
}

test('loaded legacy workflow migrates old model and resolution labels', async () => {
    for (const [old, current, label] of [
        ['Flux', 'Flux.1', '1024x1024    (1:1 Square)'],
        ['Qwen Image', 'Qwen-Image', '1920x1080    (16:9 Landscape)'],
    ]) {
        const saved = node(old, label);
        await extension.loadedGraphNode(saved);
        assert.equal(saved.widgets[0].value, current);
        assert.equal(saved.widgets[1].value.split(' ')[0], label.trim().split(' ')[0]);
        assert.ok(saved.widgets[1].options.values.includes(saved.widgets[1].value));
    }
    const saved = node('SD3', '2048x2048    (1:1 Square)');
    await extension.loadedGraphNode(saved);
    assert.equal(saved.widgets[1].value, '2048x2048 (1:1 Square)');
    assert.ok(saved.widgets[1].options.values.includes(saved.widgets[1].value));
});

test('generated legacy presets use named ratios and model multiple', async () => {
    const saved = node('HunyuanImage 2.1', '1024x1024    (1:1 Square)');
    await extension.loadedGraphNode(saved);
    const labels = saved.widgets[1].options.values;
    assert.ok(labels.length > 10);
    assert.ok(labels.length <= RATIOS.length);
    assert.ok(labels.every(label => {
        const [, width, height] = label.match(/^(\d+)x(\d+)/);
        return Number(width) % 32 === 0 && Number(height) % 32 === 0;
    }));
    assert.ok(labels.includes(saved.widgets[1].value));
    const unknown = node('Unlisted', '1024x1024    (1:1 Square)');
    await extension.loadedGraphNode(unknown);
    assert.ok(unknown.widgets[1].options.values.length > 0);
    const all = node('All', '1024x1024    (1:1 Square)');
    await extension.loadedGraphNode(all);
    assert.equal(all.widgets[1].options.values.length, 86);
    assert.ok(labels.every(label => all.widgets[1].options.values.includes(label)));
});
