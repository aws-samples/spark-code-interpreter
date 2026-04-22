// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { Fragment, memo, useEffect } from 'react';
import clsx from 'clsx';
import { useContainerQuery } from '@cloudscape-design/component-toolkit';
import styles from './styles.css.js';
export default memo(LabelsMeasure);
// Places the invisible left-hand side labels to calculate their maximum width.
function LabelsMeasure({ scale, ticks, tickFormatter, autoWidth, maxLabelsWidth }) {
    const [width, ref] = useContainerQuery(rect => rect.contentBoxWidth);
    // Tell elements's width to the parent.
    useEffect(() => {
        autoWidth(width || 0);
    }, [autoWidth, width]);
    const labelMapper = (value) => {
        const scaledValue = scale.d3Scale(value);
        if (scaledValue === undefined || !isFinite(scaledValue)) {
            return null;
        }
        const formattedValue = tickFormatter ? tickFormatter(value) : value.toString();
        const lines = (formattedValue + '').split('\n');
        return (React.createElement(Fragment, { key: `${value}` }, lines.map((line, lineIndex) => (React.createElement("div", { key: lineIndex, className: styles['labels-inline-start__label'], "aria-hidden": "true" }, line)))));
    };
    return (React.createElement("div", { ref: ref, className: clsx(styles['labels-inline-start'], styles['labels-inline-start--hidden']), style: { maxWidth: maxLabelsWidth } }, ticks.map(labelMapper)));
}
//# sourceMappingURL=labels-measure.js.map