// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import { getLogicalBoundingClientRect } from '@cloudscape-design/component-toolkit/internal';
export function isCellStatesEqual(s1, s2) {
    if (s1 && s2) {
        return (s1.padInlineStart === s2.padInlineStart &&
            s1.lastInsetInlineStart === s2.lastInsetInlineStart &&
            s1.lastInsetInlineEnd === s2.lastInsetInlineEnd &&
            s1.offset.insetInlineStart === s2.offset.insetInlineStart &&
            s1.offset.insetInlineEnd === s2.offset.insetInlineEnd);
    }
    return s1 === s2;
}
export function isWrapperStatesEqual(s1, s2) {
    return (s1.scrollPaddingInlineStart === s2.scrollPaddingInlineStart &&
        s1.scrollPaddingInlineEnd === s2.scrollPaddingInlineEnd);
}
export function updateCellOffsets(cells, props) {
    var _a, _b, _c, _d;
    const totalColumns = props.visibleColumns.length;
    const firstColumnsWidths = [];
    for (let i = 0; i < Math.min(totalColumns, props.stickyColumnsFirst); i++) {
        const element = cells.get(props.visibleColumns[i]);
        const cellWidth = element ? getLogicalBoundingClientRect(element).inlineSize : 0;
        firstColumnsWidths[i] = ((_a = firstColumnsWidths[i - 1]) !== null && _a !== void 0 ? _a : 0) + cellWidth;
    }
    const lastColumnsWidths = [];
    for (let i = 0; i < Math.min(totalColumns, props.stickyColumnsLast); i++) {
        const element = cells.get(props.visibleColumns[totalColumns - 1 - i]);
        const cellWidth = element ? getLogicalBoundingClientRect(element).inlineSize : 0;
        lastColumnsWidths[i] = ((_b = lastColumnsWidths[i - 1]) !== null && _b !== void 0 ? _b : 0) + cellWidth;
    }
    const stickyWidthInlineStart = (_c = firstColumnsWidths[props.stickyColumnsFirst - 1]) !== null && _c !== void 0 ? _c : 0;
    const stickyWidthInlineEnd = (_d = lastColumnsWidths[props.stickyColumnsLast - 1]) !== null && _d !== void 0 ? _d : 0;
    const offsets = props.visibleColumns.reduce((map, columnId, columnIndex) => {
        var _a, _b;
        return map.set(columnId, {
            first: (_a = firstColumnsWidths[columnIndex - 1]) !== null && _a !== void 0 ? _a : 0,
            last: (_b = lastColumnsWidths[totalColumns - 1 - columnIndex - 1]) !== null && _b !== void 0 ? _b : 0,
        });
    }, new Map());
    return { offsets, stickyWidthInlineStart, stickyWidthInlineEnd };
}
//# sourceMappingURL=utils.js.map