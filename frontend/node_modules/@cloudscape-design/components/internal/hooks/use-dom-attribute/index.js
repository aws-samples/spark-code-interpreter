// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import { useEffect, useRef } from 'react';
/*
 * This hook allows setting an DOM attribute after the first render, without rerendering the component.
 */
export function useDOMAttribute(elementRef, attributeName, value) {
    const attributeValueRef = useRef();
    useEffect(() => {
        var _a;
        // With this effect, we apply the attribute only on the client, to avoid hydration errors.
        attributeValueRef.current = value;
        (_a = elementRef.current) === null || _a === void 0 ? void 0 : _a.setAttribute(attributeName, value);
    }, [attributeName, value, elementRef]);
    return {
        [attributeName]: attributeValueRef.current,
    };
}
//# sourceMappingURL=index.js.map