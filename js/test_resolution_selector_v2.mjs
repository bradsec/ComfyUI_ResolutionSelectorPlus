import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import { RATIOS, getResolutions, syncSlots, install } from './resolution_selector_v2_core.js';

const modelInfo = Object.fromEntries([
    ['SD 1.5', 8], ['SDXL', 8], ['SD3', 16], ['Flux.1', 16], ['Flux.2', 16],
    ['Chroma', 16], ['Z-Image', 16], ['Qwen-Image', 16], ['Qwen-Image 2.1', 16],
    ['HiDream', 16], ['HunyuanImage 2.1', 32], ['Other (4ch /8)', 8],
].map(([name, best_multiple]) => [name, { best_multiple }]));

function makeNode() {
    const widgets = [];
    for (let slot = 1; slot <= 4; slot++) {
        for (const [name, value] of [['model', 'SDXL'], ['aspect_ratio', RATIOS[0]], ['megapixels', '1.0'],
            ['resolution', slot === 1 ? getResolutions('1:1', '1.0')[0] : 'none'], ['multiple', 8]]) {
            widgets.push({ name: `res${slot}_${name}`, value, type: 'combo', options: { values: [] } });
        }
    }
    return {
        constructor: { nodeData: { input: { required: { res1_model: [[], { model_info: modelInfo }] } } } },
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

function withKJNodes(run) {
    const previous = globalThis.LiteGraph;
    let nextId = 1;
    globalThis.LiteGraph = {
        registered_node_types: { SetNode: true },
        createNode() {
            return {
                id: nextId++, type: 'SetNode', widgets: [{ value: '' }],
                properties: {}, flags: {}, size: [120, 30],
                validateName(graph) {
                    const base = this.widgets[0].value;
                    let name = base;
                    let suffix = 2;
                    while (graph._nodes.some(other => other !== this && other.type === 'SetNode'
                        && other.widgets[0].value === name)) name = `${base}_${suffix++}`;
                    this.widgets[0].value = name;
                    this.title = `Set_${name}`;
                },
            };
        },
    };
    const graph = {
        _nodes: [],
        add(node) { node.graph = this; this._nodes.push(node); },
        remove(node) { this._nodes.splice(this._nodes.indexOf(node), 1); },
        getNodeById(id) { return this._nodes.find(node => node.id === id); },
    };
    const node = makeNode();
    node.id = nextId++;
    node.pos = [100, 100];
    node.properties = {};
    node.connect = (slot, target) => { target.inputs = [{ link: { origin_id: node.id, origin_slot: slot } }]; };
    graph.add(node);
    const menu = () => { const options = []; node.getExtraMenuOptions?.(null, options); return options; };
    const toggle = () => menu().find(option => option.content.includes('Auto Set nodes')).callback();
    const sets = () => graph._nodes.filter(item => item.type === 'SetNode');
    try { run({ node, graph, menu, toggle, sets }); } finally { globalThis.LiteGraph = previous; }
}

test('no KJNodes hides Auto Set menu', () => {
    const previous = globalThis.LiteGraph;
    globalThis.LiteGraph = { registered_node_types: {} };
    try {
        const node = makeNode();
        install(node);
        const options = [];
        node.getExtraMenuOptions?.(null, options);
        assert.deepEqual(options, []);
    } finally { globalThis.LiteGraph = previous; }
});

test('Auto Set creates, grows, shrinks and removes managed triples', () => withKJNodes(({ node, menu, toggle, sets }) => {
    install(node);
    assert.equal(menu().find(option => option.content.includes('Auto Set nodes')).content, 'Auto Set nodes (KJNodes): Off');
    toggle();
    assert.deepEqual(sets().map(item => item.widgets[0].value), ['res1_width', 'res1_height', 'res1_latent']);
    assert.deepEqual(sets().map(item => item.inputs[0].link.origin_slot), [0, 1, 2]);
    assert.ok(sets().every(item => item.flags.collapsed));
    assert.equal(menu().find(option => option.content.includes('Auto Set nodes')).content, 'Auto Set nodes (KJNodes): On');
    change(node, 'res2_resolution', getResolutions('1:1', '1.0')[0]);
    assert.deepEqual(sets().slice(3).map(item => item.widgets[0].value), ['res2_width', 'res2_height', 'res2_latent']);
    change(node, 'res2_resolution', 'none');
    assert.equal(sets().length, 3);
    toggle();
    assert.equal(sets().length, 0);
}));

test('prefix renames managed SetNodes and preserves manual nodes', () => withKJNodes(({ node, graph, menu, toggle, sets }) => {
    const manual = globalThis.LiteGraph.createNode('SetNode');
    manual.widgets[0].value = 'res1_width';
    graph.add(manual);
    install(node);
    toggle();
    assert.equal(sets()[1].widgets[0].value, 'res1_width_2');
    const previousPrompt = globalThis.prompt;
    globalThis.prompt = () => 'portrait';
    try { menu().find(option => option.content.includes('Set node prefix')).callback(); }
    finally { globalThis.prompt = previousPrompt; }
    assert.deepEqual(sets().slice(1).map(item => item.widgets[0].value),
        ['portrait_res1_width', 'portrait_res1_height', 'portrait_res1_latent']);
    toggle();
    assert.deepEqual(sets(), [manual]);
}));

test('configure reuses managed IDs; deleted SetNode returns on next sync', () => withKJNodes(({ node, graph, toggle, sets }) => {
    install(node);
    toggle();
    const saved = { ...node.properties, autoSetNodeIds: { ...node.properties.autoSetNodeIds } };
    node.onConfigure?.({});
    assert.equal(sets().length, 3);
    node.properties = saved;
    node.onConfigure?.({});
    assert.equal(sets().length, 3);
    node._resolutionSelectorV2Refresh();
    graph.remove(sets()[0]);
    assert.equal(sets().length, 2);
    node._resolutionSelectorV2Refresh();
    assert.equal(sets().length, 3);
}));

test('sync reconnects a disconnected managed SetNode', () => withKJNodes(({ node, toggle, sets }) => {
    install(node);
    toggle();
    sets()[0].inputs[0].link = null;
    node._resolutionSelectorV2Refresh();
    assert.equal(sets()[0].inputs[0].link.origin_slot, 0);
}));

test('saved managed ID waits for graph load before recreation', () => withKJNodes(({ node, graph, toggle, sets }) => {
    install(node);
    toggle();
    const savedSet = sets()[0];
    graph.remove(savedSet);
    node.onConfigure?.({});
    node._resolutionSelectorV2Refresh();
    assert.equal(sets().length, 2);
    graph.add(savedSet);
    node._resolutionSelectorV2Refresh();
    assert.equal(sets().length, 3);
}));

test('resolution candidates are filtered and unique', () => {
    const choices = getResolutions('16:9', '1.0');
    assert.ok(choices.length > 0);
    assert.equal(new Set(choices).size, choices.length);
    assert.ok(choices.every(label => label.includes('16:9')));
    assert.ok(choices.every(label => /^\d+x\d+ \(16:9\)$/.test(label)));
});

test('legacy unknown model uses All presets', () => {
    const source = readFileSync(new URL('./resolution_selector.js', import.meta.url), 'utf8')
        .replace(/^import .*\n/, '') + '\nglobalThis.unknown = getResolutionsForModel("FutureImage"); globalThis.all = getAllResolutions();';
    const context = { app: { registerExtension() {} } };
    runInNewContext(source, context);
    assert.equal(context.unknown.length, context.all.length);
});

test('legacy discovered model lists presets its best multiple divides', () => {
    const source = readFileSync(new URL('./resolution_selector.js', import.meta.url), 'utf8')
        .replace(/^import .*\n/, '') + '\nglobalThis.all = getAllResolutions(); globalThis.f32 = getResolutionsForModel("Future", { Future: { best_multiple: 32 } }); globalThis.f16 = getResolutionsForModel("Future", { Future: { best_multiple: 16 } });';
    const context = { app: { registerExtension() {} } };
    runInNewContext(source, context);
    const sides = label => label.match(/^(\d+)x(\d+)/).slice(1).map(Number);
    assert.ok(context.f32.length > 0 && context.f32.length < context.f16.length);
    assert.ok(context.f16.length < context.all.length);
    assert.ok(context.f32.every(label => sides(label).every(side => side % 32 === 0)));
    assert.ok(context.f16.every(label => sides(label).every(side => side % 16 === 0)));
    assert.ok(context.all.filter(label => sides(label).every(side => side % 32 === 0)).every(label => context.f32.includes(label)));
});

test('new model metadata drives rounding without a JS model table', () => {
    const node = makeNode();
    node.constructor.nodeData.input.required.res1_model[1].model_info = {
        ...modelInfo, FutureImage: { channels: 6, downscale: 16, rank: 4, best_multiple: 32 },
    };
    install(node);
    change(node, 'res1_model', 'FutureImage');
    assert.equal(widget(node, 'res1_multiple').value, 32);
});

test('onConfigure migrates every released bare ratio', () => {
    for (const named of RATIOS) {
        const node = makeNode();
        const bare = named.split(' ')[0];
        node.onConfigure = function () { widget(this, 'res1_aspect_ratio').value = bare; };
        install(node);
        widget(node, 'res1_resolution').value = getResolutions(named, '1.0')[0];
        const warnings = [];
        const previousWarn = console.warn;
        console.warn = message => warnings.push(message);
        try { node.onConfigure(); } finally { console.warn = previousWarn; }
        assert.equal(widget(node, 'res1_aspect_ratio').value, named);
        assert.deepEqual(widget(node, 'res1_resolution').options.values, getResolutions(named, '1.0'));
        assert.deepEqual(warnings, []);
    }
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
    change(node, 'res1_aspect_ratio', '16:9 (Widescreen)');
    assert.deepEqual(resolution.options.values, getResolutions('16:9', '1.0'));
    change(node, 'res1_resolution', valid);
    change(node, 'res1_aspect_ratio', '16:9 (Widescreen)');
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
            ['SDXL', RATIOS[0], '1.0', getResolutions('1:1', '1.0')[0], 8]);
        assert.equal(widget(node, 'res2_aspect_ratio').value, '16:9 (Widescreen)');
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
    assert.equal(Object.keys(modelInfo).length, 12);
});
