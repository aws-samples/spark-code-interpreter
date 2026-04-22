// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import { useEffect, useRef } from 'react';
import { getFirstFocusable, isFocusable } from '../components/focus-lock/utils.js';
export function useListFocusController({ nextFocusIndex, onFocusMoved, listItemSelector, fallbackSelector, showMoreSelector, }) {
    const tokenListRef = useRef(null);
    useEffect(() => {
        if (nextFocusIndex === undefined || nextFocusIndex === null || tokenListRef.current === null) {
            return;
        }
        const tokenElements = tokenListRef.current.querySelectorAll(listItemSelector);
        const fallbackElement = fallbackSelector ? selectElement(tokenListRef.current, fallbackSelector) : null;
        const toggleButton = showMoreSelector ? selectElement(tokenListRef.current, showMoreSelector) : null;
        let closestPrevIndex = Number.NEGATIVE_INFINITY;
        let closestNextIndex = Number.POSITIVE_INFINITY;
        for (let activeIndex = 0; activeIndex < tokenElements.length; activeIndex++) {
            if (activeIndex < nextFocusIndex) {
                closestPrevIndex =
                    nextFocusIndex - activeIndex < nextFocusIndex - closestPrevIndex ? activeIndex : closestPrevIndex;
            }
            else {
                closestNextIndex =
                    activeIndex - nextFocusIndex < closestNextIndex - nextFocusIndex ? activeIndex : closestNextIndex;
            }
        }
        const nextElement = tokenElements[closestNextIndex];
        const prevElement = tokenElements[closestPrevIndex];
        const focusTarget = getFirstEligible({ id: 'next', element: nextElement }, { id: 'prev', element: prevElement }, { id: 'show-more', element: toggleButton }, { id: 'fallback', element: fallbackElement });
        if (focusTarget) {
            onFocusMoved(focusTarget.element, focusTarget.id);
        }
        // Expecting onFocusMoved to be pure
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [nextFocusIndex, listItemSelector, fallbackSelector, showMoreSelector]);
    return tokenListRef;
}
function getFirstEligible(...elements) {
    for (const { id, element } of elements) {
        const focusable = element ? getFocusableElement(element) : null;
        if (focusable) {
            return { id, element: focusable };
        }
    }
    return null;
}
function getFocusableElement(element) {
    if (!(element instanceof HTMLElement)) {
        return null;
    }
    if (isFocusable(element)) {
        return element;
    }
    return getFirstFocusable(element);
}
function selectElement(container, selector) {
    if (container.matches(selector)) {
        return container;
    }
    return container.querySelector(selector);
}
//# sourceMappingURL=use-list-focus-controller.js.map