// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { memo, useEffect, useRef } from 'react';
import { getIsRtl } from '@cloudscape-design/component-toolkit/internal';
import { getTextWidth } from './responsive-text-utils';
export default memo(ResponsiveText);
function ResponsiveText({ x, y, className, children, maxWidth }) {
    const textRef = useRef(null);
    // Determine the visible width of the text and if necessary truncate it until it fits.
    useEffect(() => {
        const isRtl = getIsRtl(textRef.current);
        renderTextContent(textRef.current, children, maxWidth, isRtl);
    }, [maxWidth, children]);
    return (React.createElement("text", { ref: textRef, x: x, y: y, style: { textAnchor: 'end' }, className: className }, children));
}
export function renderTextContent(textNode, text, maxWidth, isRtl) {
    let visibleLength = text.length;
    while (visibleLength >= 0) {
        textNode.textContent = truncateText(text, visibleLength, isRtl);
        if (getTextWidth(textNode) <= maxWidth) {
            return;
        }
        else {
            visibleLength--;
        }
    }
}
function truncateText(text, maxLength, isRtl) {
    if (text.length === maxLength) {
        return text;
    }
    if (isRtl) {
        return text.slice(text.length - maxLength) + '…';
    }
    return text.slice(0, maxLength) + '…';
}
//# sourceMappingURL=index.js.map