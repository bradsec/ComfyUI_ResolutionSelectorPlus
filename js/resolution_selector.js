import { app } from "/scripts/app.js";
import { RATIOS, getResolutions } from "./resolution_selector_v2_core.js";

// Model-specific resolution presets. Mirror of MODEL_RESOLUTIONS in nodes.py:
// keep in sync (test_resolution_selector.py diffs the two tables).
const MODEL_RESOLUTIONS = {
    "Flux.1": {
        "square": [[512, 512], [768, 768], [1024, 1024], [1088, 1088], [1280, 1280], [1328, 1328], [1536, 1536], [1920, 1920], [2048, 2048]],
        "portrait": [[688, 2048], [768, 1344], [832, 1216], [896, 1152], [928, 1664], [1024, 1536], [1024, 1792], [1024, 2048], [1056, 1584], [1088, 1920], [1104, 1472], [1152, 2048], [1200, 1792], [1360, 2048], [1456, 2048], [1536, 2048], [1616, 2048], [1632, 2048], [1712, 2048]],
        "landscape": [[1280, 720], [1344, 768], [1216, 832], [1152, 896], [1472, 1104], [1536, 1024], [1584, 1056], [1664, 928], [1792, 1024], [1792, 1200], [1920, 1088], [2048, 688], [2048, 1024], [2048, 1152], [2048, 1360], [2048, 1456], [2048, 1536], [2048, 1616], [2048, 1632], [2048, 1712]],
    },
    "Qwen-Image": {
        "square": [[1024, 1024], [1080, 1080], [1280, 1280], [1328, 1328], [1536, 1536], [1920, 1920], [2048, 2048]],
        "portrait": [[680, 2048], [928, 1664], [1024, 1536], [1024, 2048], [1056, 1584], [1080, 1920], [1104, 1472], [1152, 2048], [1200, 1800], [1368, 2048], [1464, 2048], [1536, 2048], [1608, 2048], [1640, 2048], [1704, 2048]],
        "landscape": [[1280, 720], [1472, 1104], [1536, 1024], [1584, 1056], [1664, 928], [1800, 1200], [1920, 1080], [2048, 680], [2048, 1024], [2048, 1152], [2048, 1368], [2048, 1464], [2048, 1536], [2048, 1608], [2048, 1640], [2048, 1704]],
    },
    "Z-Image": {
        "square": [[512, 512], [768, 768], [1024, 1024], [1080, 1080], [1280, 1280], [1328, 1328], [1536, 1536], [1920, 1920], [2048, 2048]],
        "portrait": [[680, 2048], [720, 1280], [768, 1024], [928, 1664], [1024, 2048], [1056, 1584], [1080, 1920], [1104, 1472], [1152, 2048], [1200, 1800], [1368, 2048], [1464, 2048], [1536, 2048], [1608, 2048], [1640, 2048], [1704, 2048]],
        "landscape": [[1024, 768], [1280, 720], [1472, 1104], [1584, 1056], [1664, 928], [1800, 1200], [1920, 1080], [2048, 680], [2048, 1024], [2048, 1152], [2048, 1368], [2048, 1464], [2048, 1536], [2048, 1608], [2048, 1640], [2048, 1704]],
    },
    "SD 1.5": {
        "square": [[512, 512], [768, 768], [1024, 1024], [1080, 1080], [1280, 1280], [1536, 1536]],
        "portrait": [[512, 768], [512, 680], [512, 1024], [680, 2048], [768, 1024], [768, 1344], [1024, 2048], [1080, 1920], [1200, 1800], [1368, 2048], [1464, 2048], [1536, 2048], [1608, 2048], [1640, 2048], [1704, 2048]],
        "landscape": [[768, 512], [1024, 512], [1024, 768], [1280, 720], [1344, 768], [1536, 512], [1800, 1200], [1920, 1080], [2048, 680], [2048, 1024], [2048, 1368], [2048, 1464], [2048, 1536], [2048, 1608], [2048, 1640], [2048, 1704]],
    },
    "SDXL": {
        "square": [[1024, 1024], [1080, 1080], [1280, 1280], [1536, 1536], [1920, 1920], [2048, 2048]],
        "portrait": [[640, 1536], [680, 2048], [768, 1344], [832, 1216], [896, 1152], [1024, 1536], [1024, 2048], [1080, 1920], [1152, 2048], [1200, 1800], [1368, 2048], [1464, 2048], [1536, 2048], [1608, 2048], [1640, 2048], [1704, 2048]],
        "landscape": [[1152, 896], [1216, 832], [1280, 720], [1344, 768], [1536, 640], [1536, 1024], [1800, 1200], [1920, 1080], [2048, 680], [2048, 1024], [2048, 1152], [2048, 1368], [2048, 1464], [2048, 1536], [2048, 1608], [2048, 1640], [2048, 1704]],
    }
};

function gcd(a, b) {
    while (b !== 0) {
        const temp = b;
        b = a % b;
        a = temp;
    }
    return a;
}

function calculateAspectRatio(width, height) {
    // Calculate actual ratio as decimal
    const actualRatio = width / height;

    // Common aspect ratios [ratio_value, "width:height" string]
    const commonRatios = [
        [1.0, "1:1"],      // Square
        [1.25, "5:4"],     // 1.25
        [1.33, "4:3"],     // 1.333...
        [1.5, "3:2"],      // 1.5
        [1.6, "16:10"],    // 1.6
        [1.78, "16:9"],    // 1.777...
        [2.0, "2:1"],      // 2.0
        [2.35, "21:9"],    // 2.333... (ultrawide)
        [2.4, "12:5"],     // 2.4
        [3.0, "3:1"],      // 3.0
        // Portrait ratios
        [0.75, "3:4"],     // 0.75
        [0.67, "2:3"],     // 0.666...
        [0.625, "5:8"],    // 0.625
        [0.56, "9:16"],    // 0.5625
        [0.5, "1:2"],      // 0.5
        [0.42, "5:12"],    // 0.4166...
        [0.33, "1:3"],     // 0.333... (panoramic)
    ];

    // Find closest common ratio by absolute difference
    let closestRatio = commonRatios[0];
    let minDiff = Math.abs(actualRatio - closestRatio[0]);

    for (const ratio of commonRatios) {
        const diff = Math.abs(actualRatio - ratio[0]);
        if (diff < minDiff) {
            minDiff = diff;
            closestRatio = ratio;
        }
    }

    return closestRatio[1];
}

function formatResolution(width, height) {
    const aspectRatio = calculateAspectRatio(width, height);
    const name = RATIOS.find(ratio => ratio.startsWith(`${aspectRatio} `)).match(/\((.*)\)/)[1];
    return `${width}x${height} (${aspectRatio} ${name})`;
}

function getGeneratedResolutions(best) {
    const dimensions = new Map();
    for (const ratio of RATIOS) {
        const candidates = getResolutions(ratio, '1.0').map(label => label.match(/^(\d+)x(\d+)/).slice(1).map(Number));
        const [width, height] = candidates.reduce((a, b) =>
            Math.abs(b[0] * b[1] - 1000000) < Math.abs(a[0] * a[1] - 1000000) ? b : a);
        const w = Math.max(best, Math.floor((width + best / 2) / best) * best);
        const h = Math.max(best, Math.floor((height + best / 2) / best) * best);
        dimensions.set(`${w}x${h}`, [w, h]);
    }
    return [...dimensions.values()]
        .sort((a, b) => (a[0] === a[1] ? 0 : a[0] < a[1] ? 1 : 2)
            - (b[0] === b[1] ? 0 : b[0] < b[1] ? 1 : 2)
            || Math.max(...a) / Math.min(...a) - Math.max(...b) / Math.min(...b) || a[0] * a[1] - b[0] * b[1])
        .map(([w, h]) => formatResolution(w, h));
}

function getAllResolutions(modelInfo = {}) {
    const uniqueResolutions = new Map();

    // Collect all unique width×height pairs
    for (const modelName in MODEL_RESOLUTIONS) {
        const modelData = MODEL_RESOLUTIONS[modelName];
        for (const category of ["square", "portrait", "landscape"]) {
            if (modelData[category]) {
                for (const [w, h] of modelData[category]) {
                    const key = `${w}x${h}`;
                    if (!uniqueResolutions.has(key)) {
                        uniqueResolutions.set(key, { width: w, height: h, pixels: w * h });
                    }
                }
            }
        }
    }
    for (const [model, info] of Object.entries(modelInfo)) {
        if (MODEL_RESOLUTIONS[model] || !info?.best_multiple) continue;
        for (const label of getGeneratedResolutions(info.best_multiple)) {
            const [, width, height] = label.match(/^(\d+)x(\d+)/).map(Number);
            uniqueResolutions.set(`${width}x${height}`, { width, height, pixels: width * height });
        }
    }

    // Sort by total pixels, then by width
    const sorted = Array.from(uniqueResolutions.values())
        .sort((a, b) => {
            if (a.pixels !== b.pixels) return a.pixels - b.pixels;
            return a.width - b.width;
        });

    return sorted.map(({ width, height }) => formatResolution(width, height));
}

function getResolutionsForModel(model, modelInfo = {}) {
    model = { Flux: 'Flux.1', 'Qwen Image': 'Qwen-Image' }[model] || model;
    if (model === "All") {
        return getAllResolutions(modelInfo);
    }

    const modelData = MODEL_RESOLUTIONS[model];
    if (!modelData) {
        const best = modelInfo[model]?.best_multiple;
        return best ? getGeneratedResolutions(best) : getAllResolutions(modelInfo);
    }

    const resolutions = [];
    for (const category of ["square", "portrait", "landscape"]) {
        if (modelData[category]) {
            for (const [w, h] of modelData[category]) {
                resolutions.push(formatResolution(w, h));
            }
        }
    }
    return resolutions;
}

function getDefaultResolution(model) {
    // Model-specific native/optimal resolutions
    const defaultResolutions = {
        "Flux.1": [1024, 1024],
        "Qwen-Image": [1328, 1328],
        "Z-Image": [1024, 1024],
        "SD 1.5": [512, 512],
        "SDXL": [1024, 1024],
        "All": [1024, 1024]
    };

    if (defaultResolutions[model]) {
        const [w, h] = defaultResolutions[model];
        return formatResolution(w, h);
    }

    // Fallback
    return null;
}

function matchingResolution(saved, resolutions, model, modelInfo) {
    const dimensions = saved?.match(/^\s*(\d+)x(\d+)/);
    if (!dimensions) return null;
    const width = Number(dimensions[1]);
    const height = Number(dimensions[2]);
    const existing = resolutions.find(label => label.startsWith(`${width}x${height} `));
    if (existing) return existing;
    const curated = MODEL_RESOLUTIONS[model];
    const best = curated ? model === 'Flux.1' ? 16 : 8 : modelInfo[model]?.best_multiple || 8;
    const min = curated ? 256 : 64;
    const max = curated ? 2048 : 4096;
    if ([width, height].some(side => side < min || side > max || side % best !== 0)) return null;
    const label = formatResolution(width, height);
    resolutions.push(label);
    return label;
}

app.registerExtension({
    name: "ResolutionSelectorPlus.DynamicDropdown",

    async nodeCreated(node) {
        if (node.comfyClass !== "ResolutionSelectorPlus") return;

        // Set wider default node width to prevent text cutoff
        node.setSize([400, node.size[1]]);

        const modelWidget = node.widgets.find(w => w.name === "model");
        const resolutionWidget = node.widgets.find(w => w.name === "resolution");

        if (!modelWidget || !resolutionWidget) {
            console.error("ResolutionSelector: Required widgets not found");
            return;
        }

        const origCallback = modelWidget.callback;
        const modelInfo = node.constructor.nodeData?.input?.required?.model?.[1]?.model_info
            || modelWidget.options?.model_info || {};

        const updateResolutions = (modelValue, preserve = false) => {
            modelValue = { Flux: 'Flux.1', 'Qwen Image': 'Qwen-Image' }[modelValue] || modelValue;
            modelWidget.value = modelValue;
            const resolutions = getResolutionsForModel(modelValue, modelInfo);

            if (resolutions.length === 0) {
                console.warn(`ResolutionSelector: No resolutions found for model ${modelValue}`);
                return;
            }

            resolutionWidget.options.values = resolutions;

            // Set to model-specific default resolution
            const defaultRes = getDefaultResolution(modelValue);
            const migrated = preserve && matchingResolution(resolutionWidget.value, resolutions, modelValue, modelInfo);
            if (migrated) {
                resolutionWidget.value = migrated;
            } else if (resolutions.includes(defaultRes)) {
                resolutionWidget.value = defaultRes;
            } else if (!resolutions.includes(resolutionWidget.value)) {
                // Fallback to first resolution if default not found
                resolutionWidget.value = resolutions[0];
            }

            node.setDirtyCanvas(true, true);
        };

        modelWidget.callback = function(value) {
            if (origCallback) {
                origCallback.apply(this, arguments);
            }
            updateResolutions(value);
        };

        setTimeout(() => {
            updateResolutions(modelWidget.value, true);
        }, 10);
    },

    async loadedGraphNode(node) {
        if (node.comfyClass !== "ResolutionSelectorPlus") return;

        const modelWidget = node.widgets.find(w => w.name === "model");
        if (modelWidget) {
            modelWidget.value = { Flux: 'Flux.1', 'Qwen Image': 'Qwen-Image' }[modelWidget.value] || modelWidget.value;
            const modelInfo = node.constructor.nodeData?.input?.required?.model?.[1]?.model_info
                || modelWidget.options?.model_info || {};
            const resolutions = getResolutionsForModel(modelWidget.value, modelInfo);
            const resolutionWidget = node.widgets.find(w => w.name === "resolution");

            if (resolutionWidget && resolutions.length > 0) {
                resolutionWidget.options.values = resolutions;

                const migrated = matchingResolution(resolutionWidget.value, resolutions, modelWidget.value, modelInfo);
                if (migrated) {
                    resolutionWidget.value = migrated;
                } else if (!resolutions.includes(resolutionWidget.value)) {
                    console.warn(`ResolutionSelector: saved resolution "${resolutionWidget.value}" is not valid for model ${modelWidget.value}; reset to ${resolutions[0]}`);
                    resolutionWidget.value = resolutions[0];
                }
            }
        }
    }
});
