import { app } from '/scripts/app.js';
import { install } from './resolution_selector_v2_core.js';

app.registerExtension({
    name: 'ResolutionSelectorPlus.v2',
    nodeCreated(node) {
        if (node.comfyClass === 'ResolutionSelectorPlusV2') install(node);
    },
    loadedGraphNode(node) {
        if (node.comfyClass === 'ResolutionSelectorPlusV2') {
            install(node);
            node._resolutionSelectorV2Refresh();
        }
    },
});
