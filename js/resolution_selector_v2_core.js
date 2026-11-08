export const RATIOS = ['1:1 (Square)', '5:4 (Large Format)', '4:3 (Standard)',
    '3:4 (Portrait Standard)', '3:2 (Photo)', '2:3 (Portrait Photo)',
    '16:10 (Widescreen Monitor)', '5:8 (Portrait Widescreen Monitor)',
    '16:9 (Widescreen)', '9:16 (Portrait Widescreen)', '2:1 (Univisium)',
    '1:2 (Portrait Univisium)', '21:9 (Ultrawide)', '12:5 (Cinemascope)',
    '5:12 (Portrait Cinemascope)', '3:1 (Panorama)', '1:3 (Portrait Panorama)'];
const BARE_RATIOS = RATIOS.map(name => name.split(' ')[0]);
export const MEGAPIXELS = ['0.25', '0.5', '1.0', '1.5', '2.0', '4.0'];
const APPROX = [1, 1.25, 1.33, 0.75, 1.5, 0.67, 1.6, 0.625, 1.78, 0.56,
    2, 0.5, 2.35, 2.4, 0.42, 3, 0.33];

export function getResolutions(ratio, megapixels) {
    const bare = RATIOS.includes(ratio) ? ratio.split(' ')[0] : ratio;
    if (!BARE_RATIOS.includes(bare) || !MEGAPIXELS.includes(megapixels)) throw new Error('Unsupported ratio or megapixels');
    const [numerator, denominator] = bare.split(':').map(Number);
    const value = numerator / denominator;
    const choices = [];
    for (const scale of [0.9, 1, 1.1]) {
        const pixels = Number(megapixels) * 1000000 * scale;
        for (const snap of [64, 32, 16, 8]) {
            const width = Math.max(64, Math.floor(Math.sqrt(pixels * value) / snap + 0.5) * snap);
            const height = Math.max(64, Math.floor(Math.sqrt(pixels / value) / snap + 0.5) * snap);
            const actual = width / height;
            let index = 0;
            for (let i = 1; i < BARE_RATIOS.length; i++) {
                if (Math.abs(actual - APPROX[i]) < Math.abs(actual - APPROX[index])) index = i;
            }
            if (BARE_RATIOS[index] !== bare) continue;
            const label = `${width}x${height} (${bare})`;
            if (!choices.includes(label)) choices.push(label);
            break;
        }
    }
    return choices;
}

export function syncSlots(node) {
    const widget = name => node.widgets.find(item => item.name === name);
    let count = 1;
    for (let slot = 2; slot <= 4; slot++) {
        if (widget(`res${slot}_resolution`)?.value === 'none') break;
        count++;
    }
    for (let slot = count + 1; slot <= 4; slot++) {
        const resolution = widget(`res${slot}_resolution`);
        if (resolution) resolution.value = 'none';
    }
    while (node.outputs.length < count * 3) {
        const slot = Math.floor(node.outputs.length / 3) + 1;
        for (const [kind, type] of [['width', 'INT'], ['height', 'INT'], ['latent', 'LATENT']]) {
            node.addOutput(`res${slot}_${kind}`, type);
        }
    }
    while (node.outputs.length > count * 3) node.removeOutput(node.outputs.length - 1);
    return count;
}

function syncSetNodes(node, count) {
    if (!globalThis.LiteGraph?.registered_node_types?.SetNode || !node.graph) return;
    const ids = node.properties.autoSetNodeIds ??= {};
    const graph = node.graph;
    const prefix = node.properties.setNodePrefix
        ? `${node.properties.setNodePrefix.replace(/_+$/, '')}_` : '';
    const active = new Set(node.outputs.slice(0, count * 3).map(output => output.name));
    for (const [output, id] of Object.entries(ids)) {
        if (node.properties.autoSetNodes && active.has(output)) continue;
        const managed = graph.getNodeById(id);
        if (managed?.type === 'SetNode') graph.remove(managed);
        delete ids[output];
    }
    if (!node.properties.autoSetNodes) return;
    node.outputs.slice(0, count * 3).forEach((output, slot) => {
        let managed = graph.getNodeById(ids[output.name]);
        let created = false;
        if (!managed || managed.type !== 'SetNode') {
            if (node._resolutionSelectorV2DeferMissingSetNodes && ids[output.name]) return;
            managed = globalThis.LiteGraph.createNode('SetNode');
            if (!managed) return;
            managed.pos = [node.pos[0] + node.size[0] + 30, node.pos[1] + slot * 60];
            graph.add(managed);
            managed.flags.collapsed = true;
            ids[output.name] = managed.id;
            created = true;
        }
        if (created || (!node._resolutionSelectorV2DeferMissingSetNodes && !(managed.isInputConnected?.(0) ?? managed.inputs?.[0]?.link != null))) {
            node.connect(slot, managed, 0);
        }
        const name = `${prefix}${output.name}`;
        const current = managed.widgets[0].value;
        if (current !== name && !(current.startsWith(`${name}_`)
            && /^\d+$/.test(current.slice(name.length + 1)))) {
            managed.widgets[0].value = name;
            managed.validateName?.(graph);
            if (managed.widgets[0].value !== name && !node._resolutionSelectorV2SetNameWarned) {
                console.warn('Resolution Selector Plus: SetNode name already exists; using a suffix');
                node._resolutionSelectorV2SetNameWarned = true;
            }
            managed.update?.();
            managed.properties.previousName = managed.widgets[0].value;
        }
    });
    delete node._resolutionSelectorV2DeferMissingSetNodes;
    node.setDirtyCanvas?.(true, true);
}

export function install(node) {
    if (node._resolutionSelectorV2Installed) return;
    node._resolutionSelectorV2Installed = true;
    const widget = name => node.widgets?.find(item => item.name === name);
    const modelInfo = node.constructor.nodeData?.input?.required?.res1_model?.[1]?.model_info
        || widget('res1_model')?.options?.model_info || {};
    const repair = (item, values, fallback) => {
        if (item && !values.includes(item.value)) {
            item.value = fallback;
            if (!node._resolutionSelectorV2Warned) {
                console.warn('Resolution Selector Plus: invalid saved widget value; using defaults');
                node._resolutionSelectorV2Warned = true;
            }
        }
    };
    const refresh = (preserve = true, resize = true) => {
        for (let slot = 1; slot <= 4; slot++) {
            const resolution = widget(`res${slot}_resolution`);
            if (!resolution) continue;
            repair(widget(`res${slot}_model`), Object.keys(modelInfo), 'SDXL');
            repair(widget(`res${slot}_aspect_ratio`), RATIOS, RATIOS[0]);
            repair(widget(`res${slot}_megapixels`), MEGAPIXELS, '1.0');
            repair(widget(`res${slot}_multiple`), [8, 16, 32, 64], 8);
            const choices = getResolutions(widget(`res${slot}_aspect_ratio`).value,
                widget(`res${slot}_megapixels`).value);
            resolution.options.values = slot === 1 ? choices : ['none', ...choices];
            if (preserve) repair(resolution, resolution.options.values, slot === 1 ? choices[0] : 'none');
            else {
                resolution.value = slot === 1 ? choices[0] : 'none';
            }
        }
        const count = resize ? syncSlots(node) : 4;
        if (resize) syncSetNodes(node, count);
        for (let slot = 2; slot <= 4; slot++) {
            const visible = slot <= count + 1;
            for (const name of ['model', 'aspect_ratio', 'megapixels', 'resolution', 'multiple']) {
                const item = widget(`res${slot}_${name}`);
                if (!item) continue;
                item.type = visible ? item._resolutionSelectorV2Type : 'hidden';
            }
        }
        const size = node.computeSize?.() ?? node.size;
        if (size) node.setSize?.([Math.max(node.size?.[0] ?? 0, 340), size[1]]);
        node.setDirtyCanvas?.(true, true);
    };
    for (let slot = 1; slot <= 4; slot++) {
        for (const name of ['model', 'aspect_ratio', 'megapixels', 'resolution', 'multiple']) {
            const item = widget(`res${slot}_${name}`);
            if (!item) continue;
            item.label = `Res ${slot} ${name.replace('_', ' ')}`;
            item._resolutionSelectorV2Type = item.type;
            if (name === 'model' || name === 'multiple') continue;
            const previous = item.callback;
            item.callback = function (...args) {
                previous?.apply(this, args);
                refresh();
            };
        }
    }
    for (let slot = 1; slot <= 4; slot++) {
        const model = widget(`res${slot}_model`);
        if (!model) continue;
        const previous = model.callback;
        model.callback = function (...args) {
            previous?.apply(this, args);
            widget(`res${slot}_multiple`).value = modelInfo[model.value]?.best_multiple ?? 8;
            refresh();
        };
    }
    const previousConfigure = node.onConfigure;
    node.onConfigure = function (...args) {
        const result = previousConfigure?.apply(this, args);
        this._resolutionSelectorV2DeferMissingSetNodes = true;
        const batch = widget('batch_size');
        if (batch && batch.value == null) batch.value = 1;
        for (let slot = 1; slot <= 4; slot++) {
            const ratio = widget(`res${slot}_aspect_ratio`);
            const index = BARE_RATIOS.indexOf(ratio?.value);
            if (index >= 0) ratio.value = RATIOS[index];
        }
        refresh(true, false);
        return result;
    };
    const previousMenu = node.getExtraMenuOptions;
    node.getExtraMenuOptions = function (_, options) {
        previousMenu?.apply(this, arguments);
        if (!globalThis.LiteGraph?.registered_node_types?.SetNode) return;
        options.push({
            content: `Auto Set nodes (KJNodes): ${this.properties?.autoSetNodes ? 'On' : 'Off'}`,
            callback: () => {
                this.properties ??= {};
                this.properties.autoSetNodes = !this.properties.autoSetNodes;
                refresh();
            },
        }, {
            content: 'Set node prefix...',
            callback: () => {
                const prefix = globalThis.prompt?.('Set node prefix', this.properties?.setNodePrefix ?? '');
                if (prefix === null || prefix === undefined) return;
                this.properties ??= {};
                this.properties.setNodePrefix = prefix;
                refresh();
            },
        });
    };
    node._resolutionSelectorV2Refresh = refresh;
    refresh();
}
