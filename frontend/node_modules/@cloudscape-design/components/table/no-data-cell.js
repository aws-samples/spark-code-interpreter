// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useRef } from 'react';
import clsx from 'clsx';
import { useResizeObserver } from '@cloudscape-design/component-toolkit/internal';
import InternalLiveRegion from '../live-region/internal';
import InternalStatusIndicator from '../status-indicator/internal';
import styles from './styles.css.js';
export function NoDataCell({ totalColumnsCount, hasFooter, loading, loadingText, empty, tableRef, containerRef, }) {
    const cellContentRef = useRef(null);
    useResizeObserver(containerRef, ({ contentBoxWidth: containerInlineSize }) => {
        if (tableRef.current && cellContentRef.current) {
            const tablePaddingInlineStart = parseFloat(getComputedStyle(tableRef.current).paddingInlineStart) || 0;
            const tablePaddingInlineEnd = parseFloat(getComputedStyle(tableRef.current).paddingInlineEnd) || 0;
            const inlineSize = containerInlineSize + tablePaddingInlineStart + tablePaddingInlineEnd;
            cellContentRef.current.style.inlineSize = Math.floor(inlineSize) + 'px';
        }
    });
    return (React.createElement("td", { colSpan: totalColumnsCount, className: clsx(styles['cell-merged'], hasFooter && styles['has-footer']) },
        React.createElement("div", { ref: cellContentRef, className: styles['cell-merged-content'], "data-awsui-table-suppress-navigation": true }, loading ? (React.createElement(InternalStatusIndicator, { type: "loading", className: styles.loading, wrapText: true },
            React.createElement(InternalLiveRegion, { tagName: "span" }, loadingText))) : (React.createElement("div", { className: styles.empty }, empty)))));
}
//# sourceMappingURL=no-data-cell.js.map