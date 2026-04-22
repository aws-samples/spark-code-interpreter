// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import { useCallback, useState } from 'react';
import { useResizeObserver } from '@cloudscape-design/component-toolkit/internal';
export function useObservedElement(rootElementRef, selector) {
    const getElement = useCallback(() => {
        var _a, _b;
        const document = (_b = (_a = rootElementRef.current) === null || _a === void 0 ? void 0 : _a.ownerDocument) !== null && _b !== void 0 ? _b : window.document;
        return document.querySelector(selector);
    }, [rootElementRef, selector]);
    const [height, setHeight] = useState(0);
    useResizeObserver(getElement, entry => setHeight(entry.borderBoxHeight));
    return height;
}
//# sourceMappingURL=use-observed-element.js.map