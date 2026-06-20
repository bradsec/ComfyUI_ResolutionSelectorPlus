import { app } from "/scripts/app.js";

// Model-specific resolution presets with constraints
// Includes: model-optimized sizes + photo print (4x6, 5x7, 8x10) + digital/social + canvas art ratios
const MODEL_RESOLUTIONS = {
    "Flux": {
        "square": [[512, 512], [768, 768], [1024, 1024], [1088, 1088], [1280, 1280], [1536, 1536], [1920, 1920], [2048, 2048]],
        "portrait": [[688, 2048], [768, 1344], [832, 1216], [896, 1152], [928, 1664], [1024, 1536], [1024, 1792], [1024, 2048], [1088, 1920], [1152, 2048], [1200, 1792], [1360, 2048], [1456, 2048], [1536, 2048], [1616, 2048], [1632, 2048], [1712, 2048]],
        "landscape": [[1280, 720], [1344, 768], [1216, 832], [1152, 896], [1536, 1024], [1664, 928], [1792, 1024], [1792, 1200], [1920, 1088], [2048, 688], [2048, 1024], [2048, 1152], [2048, 1360], [2048, 1456], [2048, 1536], [2048, 1616], [2048, 1632], [2048, 1712]],
    },
    "Qwen Image": {
        "square": [[1024, 1024], [1080, 1080], [1280, 1280], [1328, 1328], [1536, 1536], [1920, 1920], [2048, 2048]],
        "portrait": [[680, 2048], [928, 1664], [1024, 1536], [1024, 2048], [1080, 1920], [1140, 1472], [1152, 2048], [1200, 1800], [1368, 2048], [1464, 2048], [1536, 2048], [1608, 2048], [1640, 2048], [1704, 2048]],
        "landscape": [[1280, 720], [1472, 1140], [1536, 1024], [1664, 928], [1800, 1200], [1920, 1080], [2048, 680], [2048, 1024], [2048, 1152], [2048, 1368], [2048, 1464], [2048, 1536], [2048, 1608], [2048, 1640], [2048, 1704]],
    },
    "Z-Image": {
        "square": [[512, 512], [768, 768], [1024, 1024], [1080, 1080], [1280, 1280], [1536, 1536], [1920, 1920], [2048, 2048]],
        "portrait": [[680, 2048], [720, 1280], [768, 1024], [1024, 2048], [1080, 1920], [1152, 2048], [1200, 1800], [1368, 2048], [1464, 2048], [1536, 2048], [1608, 2048], [1640, 2048], [1704, 2048]],
        "landscape": [[1024, 768], [1280, 720], [1800, 1200], [1920, 1080], [2048, 680], [2048, 1024], [2048, 1152], [2048, 1368], [2048, 1464], [2048, 1536], [2048, 1608], [2048, 1640], [2048, 1704]],
    },
    "SD 1.5": {
        "square": [[512, 512], [768, 768], [1024, 1024], [1080, 1080], [1280, 1280], [1536, 1536]],
        "portrait": [[512, 768], [512, 682], [512, 1024], [680, 2048], [768, 1024], [768, 1344], [1024, 2048], [1080, 1920], [1200, 1800], [1368, 2048], [1464, 2048], [1536, 2048], [1608, 2048], [1640, 2048], [1704, 2048]],
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
    let orientation;

    if (width === height) {
        orientation = "Square";
    } else if (width < height) {
        orientation = "Portrait";
    } else {
        orientation = "Landscape";
    }

    // Format with fixed width for better alignment
    const resolutionStr = `${width}x${height}`;
    const paddedResolution = resolutionStr.padEnd(13, ' '); // Pad to 13 chars for alignment

    return `${paddedResolution}(${aspectRatio} ${orientation})`;
}

function getAllResolutions() {
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

    // Sort by total pixels, then by width
    const sorted = Array.from(uniqueResolutions.values())
        .sort((a, b) => {
            if (a.pixels !== b.pixels) return a.pixels - b.pixels;
            return a.width - b.width;
        });

    return sorted.map(({ width, height }) => formatResolution(width, height));
}

function getResolutionsForModel(model) {
    if (model === "All") {
        return getAllResolutions();
    }

    const modelData = MODEL_RESOLUTIONS[model];
    if (!modelData) return [];

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
        "Flux": [1024, 1024],
        "Qwen Image": [1328, 1328],
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
    return formatResolution(1024, 1024);
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

        const updateResolutions = (modelValue) => {
            const resolutions = getResolutionsForModel(modelValue);

            if (resolutions.length === 0) {
                console.warn(`ResolutionSelector: No resolutions found for model ${modelValue}`);
                return;
            }

            resolutionWidget.options.values = resolutions;

            // Set to model-specific default resolution
            const defaultRes = getDefaultResolution(modelValue);
            if (resolutions.includes(defaultRes)) {
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
            updateResolutions(modelWidget.value);
        }, 10);
    },

    async loadedGraphNode(node) {
        if (node.comfyClass !== "ResolutionSelectorPlus") return;

        const modelWidget = node.widgets.find(w => w.name === "model");
        if (modelWidget) {
            const resolutions = getResolutionsForModel(modelWidget.value);
            const resolutionWidget = node.widgets.find(w => w.name === "resolution");

            if (resolutionWidget && resolutions.length > 0) {
                resolutionWidget.options.values = resolutions;

                if (!resolutions.includes(resolutionWidget.value)) {
                    resolutionWidget.value = resolutions[0];
                }
            }
        }
    }
});
