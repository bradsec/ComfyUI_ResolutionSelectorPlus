export const RATIOS = ['1:1', '5:4', '4:3', '3:2', '16:10', '16:9', '2:1', '21:9', '12:5', '3:1',
    '3:4', '2:3', '5:8', '9:16', '1:2', '5:12', '1:3'];
export const MEGAPIXELS = ['0.25', '0.5', '1.0', '1.5', '2.0', '4.0'];
export const BEST_MULTIPLES = {
    'SD 1.5': 8, SDXL: 8, SD3: 16, 'Flux.1': 16, 'Flux.2': 16, Chroma: 16,
    'Z-Image': 16, 'Qwen-Image': 16, 'Qwen-Image 2.1': 16, HiDream: 16,
    'HunyuanImage 2.1': 32, 'Other (4ch /8)': 8,
};
const APPROX = [1, 1.25, 1.33, 1.5, 1.6, 1.78, 2, 2.35, 2.4, 3,
    0.75, 0.67, 0.625, 0.56, 0.5, 0.42, 0.33];

export function getResolutions(ratio, megapixels) {
    if (!RATIOS.includes(ratio) || !MEGAPIXELS.includes(megapixels)) throw new Error('Unsupported ratio or megapixels');
    const [numerator, denominator] = ratio.split(':').map(Number);
    const value = numerator / denominator;
    const choices = [];
    for (const scale of [0.9, 1, 1.1]) {
        const pixels = Number(megapixels) * 1000000 * scale;
        for (const snap of [64, 32, 16, 8]) {
            const width = Math.max(64, Math.floor(Math.sqrt(pixels * value) / snap + 0.5) * snap);
            const height = Math.max(64, Math.floor(Math.sqrt(pixels / value) / snap + 0.5) * snap);
            const actual = width / height;
            let index = 0;
            for (let i = 1; i < RATIOS.length; i++) {
                if (Math.abs(actual - APPROX[i]) < Math.abs(actual - APPROX[index])) index = i;
            }
            if (RATIOS[index] !== ratio) continue;
            const label = `${width}x${height} (${RATIOS[index]})`;
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

export function install(node) {
    if (node._resolutionSelectorV2Installed) return;
    node._resolutionSelectorV2Installed = true;
    const widget = name => node.widgets?.find(item => item.name === name);
    const repair = (item, values, fallback) => {
        if (item && !values.includes(item.value)) {
            item.value = fallback;
            if (!node._resolutionSelectorV2Warned) {
                console.warn('Resolution Selector Plus v2: invalid saved widget value; using defaults');
                node._resolutionSelectorV2Warned = true;
            }
        }
    };
    const refresh = (preserve = true, resize = true) => {
        for (let slot = 1; slot <= 4; slot++) {
            const resolution = widget(`res${slot}_resolution`);
            if (!resolution) continue;
            repair(widget(`res${slot}_model`), Object.keys(BEST_MULTIPLES), 'SDXL');
            repair(widget(`res${slot}_aspect_ratio`), RATIOS, '1:1');
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
            widget(`res${slot}_multiple`).value = BEST_MULTIPLES[model.value];
            refresh();
        };
    }
    const previousConfigure = node.onConfigure;
    node.onConfigure = function (...args) {
        const result = previousConfigure?.apply(this, args);
        refresh(true, false);
        return result;
    };
    node._resolutionSelectorV2Refresh = refresh;
    refresh();
}
