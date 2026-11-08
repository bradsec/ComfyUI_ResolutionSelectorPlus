import test from 'node:test';
import assert from 'node:assert/strict';
import { getResolutions, syncSlots, install, BEST_MULTIPLES } from './resolution_selector_v2_core.js';

function makeNode() {
    const widgets = [];
    for (let slot = 1; slot <= 4; slot++) {
        for (const [name, value] of [['model', 'SDXL'], ['aspect_ratio', '1:1'], ['megapixels', '1.0'],
            ['resolution', slot === 1 ? getResolutions('1:1', '1.0')[0] : 'none'], ['multiple', 8]]) {
            widgets.push({ name: `res${slot}_${name}`, value, type: 'combo', options: { values: [] } });
        }
    }
    return {
        widgets, outputs: [], removed: [], links: new Set(),
        addOutput(name, type) { this.outputs.push({ name, type, links: [] }); },
        removeOutput(index) {
            this.removed.push(this.outputs[index]);
            for (const link of this.outputs[index].links) this.links.delete(link);
            this.outputs.splice(index, 1);
        },
        size: [200, 500],
        computeSize() { return [200, 100 + this.widgets.filter(item => item.type !== 'hidden').length * 10]; },
        setSize(size) { this.size = size; }, setDirtyCanvas() {},
    };
}

const widget = (node, name) => node.widgets.find(item => item.name === name);
function change(node, name, value) {
    const item = widget(node, name);
    item.value = value;
    item.callback?.(value);
}

test('resolution candidates are filtered and unique', () => {
    const choices = getResolutions('16:9', '1.0');
    assert.ok(choices.length > 0);
    assert.equal(new Set(choices).size, choices.length);
    assert.ok(choices.every(label => label.includes('16:9')));
    assert.ok(choices.every(label => /^\d+x\d+ \(16:9\)$/.test(label)));
});

test('labels and size follow visible slots', () => {
    const node = makeNode();
    install(node);
    assert.deepEqual(node.size, [340, 200]);
    assert.deepEqual(node.widgets.slice(0, 5).map(item => item.label),
        ['Res 1 model', 'Res 1 aspect ratio', 'Res 1 megapixels', 'Res 1 resolution', 'Res 1 multiple']);
    change(node, 'res2_resolution', getResolutions('1:1', '1.0')[0]);
    assert.deepEqual(node.size, [340, 250]);
    assert.equal(widget(node, 'res4_model').label, 'Res 4 model');
    change(node, 'res2_resolution', 'none');
    assert.deepEqual(node.size, [340, 200]);
});

test('outputs grow and shrink at the tail', () => {
    const node = {
        widgets: [
            { name: 'res2_resolution', value: 'none' },
            { name: 'res3_resolution', value: 'none' },
            { name: 'res4_resolution', value: 'none' },
        ],
        outputs: Array.from({ length: 3 }, (_, i) => ({ name: `res1_${i}` })),
        addOutput(name, type) { this.outputs.push({ name, type }); },
        removeOutput(index) { this.outputs.splice(index, 1); },
    };
    node.widgets[0].value = 'active';
    syncSlots(node);
    assert.equal(node.outputs.length, 6);
    node.outputs[3].links = [42];
    node.widgets[1].value = 'active';
    syncSlots(node);
    assert.equal(node.outputs.length, 9);
    assert.deepEqual(node.outputs[3].links, [42]);
    node.widgets[0].value = 'none';
    syncSlots(node);
    assert.equal(node.outputs.length, 3);
    assert.equal(node.widgets[1].value, 'none');
});

test('ratio and megapixels filter options, retaining valid and resetting invalid values', () => {
    const node = makeNode();
    install(node);
    const resolution = widget(node, 'res1_resolution');
    const valid = getResolutions('16:9', '1.0')[1];
    change(node, 'res1_aspect_ratio', '16:9');
    assert.deepEqual(resolution.options.values, getResolutions('16:9', '1.0'));
    change(node, 'res1_resolution', valid);
    change(node, 'res1_aspect_ratio', '16:9');
    assert.equal(resolution.value, valid);
    change(node, 'res1_megapixels', '2.0');
    assert.deepEqual(resolution.options.values, getResolutions('16:9', '2.0'));
    assert.equal(resolution.value, getResolutions('16:9', '2.0')[0]);
});

test('res2 and res3 grow outputs and removing res2 clears the tail links', () => {
    const node = makeNode();
    install(node);
    assert.equal(widget(node, 'res3_model').type, 'hidden');
    assert.equal(widget(node, 'res3_multiple').type, 'hidden');
    change(node, 'res2_resolution', getResolutions('1:1', '1.0')[0]);
    assert.equal(node.outputs.length, 6);
    assert.equal(widget(node, 'res3_model').type, 'combo');
    assert.equal(widget(node, 'res3_multiple').type, 'combo');
    node.outputs[3].links = [42];
    node.links.add(42);
    change(node, 'res3_resolution', getResolutions('1:1', '1.0')[0]);
    assert.equal(node.outputs.length, 9);
    node.outputs[6].links = [43];
    node.links.add(43);
    change(node, 'res2_resolution', 'none');
    assert.equal(node.outputs.length, 3);
    assert.equal(widget(node, 'res3_resolution').value, 'none');
    assert.deepEqual(node.removed.filter(output => output.links.length).map(output => output.links[0]), [43, 42]);
    assert.equal(node.links.size, 0);
});

test('install does not wrap callbacks twice', () => {
    const node = makeNode();
    install(node);
    const callback = widget(node, 'res1_aspect_ratio').callback;
    install(node);
    assert.equal(widget(node, 'res1_aspect_ratio').callback, callback);
});

test('onConfigure preserves saved links until graph load completes', () => {
    const node = makeNode();
    node.onConfigure = function (saved) {
        widget(this, 'res2_resolution').value = saved.resolution;
        this.outputs = Array.from({ length: 6 }, (_, index) => ({ name: `saved_${index}`, links: index === 3 ? [42] : [] }));
    };
    install(node);
    node.onConfigure({ resolution: getResolutions('1:1', '1.0')[0] });
    assert.equal(node.outputs[3].links[0], 42);
    node._resolutionSelectorV2Refresh();
    assert.equal(node.outputs.length, 6);
    assert.equal(node.outputs[3].links[0], 42);
});

test('outputs keep raw res names through grow, shrink, regrow, and configure', () => {
    const node = makeNode();
    node.onConfigure = function () {
        this.outputs = Array.from({ length: 6 }, (_, index) => ({
            name: `res${Math.floor(index / 3) + 1}_${['width', 'height', 'latent'][index % 3]}`,
            links: index === 3 ? [42] : [],
        }));
    };
    const labels = count => Array.from({ length: count * 3 }, (_, index) =>
        `res${Math.floor(index / 3) + 1}_${['width', 'height', 'latent'][index % 3]}`);
    const assertLabels = count => assert.deepEqual(node.outputs.map(output => output.label ?? output.name), labels(count));
    install(node);
    assertLabels(1);
    change(node, 'res2_resolution', getResolutions('1:1', '1.0')[0]);
    assertLabels(2);
    change(node, 'res3_resolution', getResolutions('1:1', '1.0')[0]);
    assertLabels(3);
    change(node, 'res2_resolution', 'none');
    assertLabels(1);
    change(node, 'res2_resolution', getResolutions('1:1', '1.0')[0]);
    assertLabels(2);
    node.onConfigure();
    assertLabels(2);
    assert.deepEqual(node.outputs[3].links, [42]);
});

test('onConfigure repairs shifted values without losing saved outputs', () => {
    const node = makeNode();
    node.onConfigure = function (saved) {
        this.widgets.forEach((item, index) => { item.value = saved.widgets_values[index]; });
        this.outputs = Array.from({ length: 6 }, (_, index) => ({ name: `saved_${index}`, links: index === 3 ? [42] : [] }));
    };
    const warnings = [];
    const previousWarn = console.warn;
    console.warn = (...args) => warnings.push(args);
    try {
        install(node);
        const saved = node.widgets.map(item => item.value);
        saved.splice(0, 5, 'bad model', 'bad ratio', 'bad MP', 'bad resolution', 12);
        saved.splice(5, 5, 'Flux.1', '16:9', '1.0', getResolutions('16:9', '1.0')[0], 64);
        saved[10] = 'bad model';
        assert.doesNotThrow(() => node.onConfigure({ widgets_values: saved }));
        assert.deepEqual(node.widgets.slice(0, 5).map(item => item.value),
            ['SDXL', '1:1', '1.0', getResolutions('1:1', '1.0')[0], 8]);
        assert.equal(widget(node, 'res2_multiple').value, 64);
        assert.equal(widget(node, 'res3_model').value, 'SDXL');
        assert.equal(node.outputs[3].links[0], 42);
        assert.doesNotThrow(() => node._resolutionSelectorV2Refresh());
        assert.equal(node.outputs[3].links[0], 42);
        assert.equal(warnings.length, 1);
    } finally {
        console.warn = previousWarn;
    }
});

test('slot 2 model change uses best multiple without changing other slots or saved overrides', () => {
    const node = makeNode();
    install(node);
    change(node, 'res2_model', 'HunyuanImage 2.1');
    assert.equal(widget(node, 'res2_multiple').value, 32);
    assert.equal(widget(node, 'res1_multiple').value, 8);
    assert.equal(widget(node, 'res3_multiple').value, 8);
    change(node, 'res2_model', 'Flux.1');
    assert.equal(widget(node, 'res2_multiple').value, 16);
    widget(node, 'res2_multiple').value = 64;
    node.onConfigure?.({});
    assert.equal(widget(node, 'res2_multiple').value, 64);
    assert.equal(Object.keys(BEST_MULTIPLES).length, 12);
});
