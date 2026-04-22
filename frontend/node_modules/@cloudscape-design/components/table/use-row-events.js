// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import { findUpUntil } from '@cloudscape-design/component-toolkit/dom';
import { fireCancelableEvent, fireNonCancelableEvent } from '../internal/events/index';
import styles from './styles.css.js';
export function useRowEvents({ onRowClick, onRowContextMenu }) {
    const onRowClickHandler = (rowIndex, item, event) => {
        const tableCell = findUpUntil(event.target, element => element.tagName.toLowerCase() === 'td');
        if (!tableCell || !tableCell.classList.contains(styles['selection-control'])) {
            const details = { rowIndex, item };
            fireNonCancelableEvent(onRowClick, details);
        }
    };
    const onRowContextMenuHandler = (rowIndex, item, event) => {
        const details = {
            rowIndex,
            item,
            clientX: event.clientX,
            clientY: event.clientY,
        };
        fireCancelableEvent(onRowContextMenu, details, event);
    };
    return {
        onRowClickHandler: onRowClick && onRowClickHandler,
        onRowContextMenuHandler: onRowContextMenu && onRowContextMenuHandler,
    };
}
//# sourceMappingURL=use-row-events.js.map