// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
/* istanbul ignore file */
export function setFunnelMetrics(funnelMetrics) {
    FunnelMetrics = funnelMetrics;
}
export function setPerformanceMetrics(performanceMetrics) {
    PerformanceMetrics = performanceMetrics;
}
export function setComponentMetrics(componentMetrics) {
    ComponentMetrics = componentMetrics;
}
/**
 * This is a stub implementation of the FunnelMetrics interface and will be replaced during
 * build time with the actual implementation.
 */
export let FunnelMetrics = {
    funnelStart() {
        return '';
    },
    funnelError() { },
    funnelComplete() { },
    funnelSuccessful() { },
    funnelCancelled() { },
    funnelChange() { },
    funnelStepStart() { },
    funnelStepComplete() { },
    funnelStepNavigation() { },
    funnelStepError() { },
    funnelStepChange() { },
    funnelSubStepStart() { },
    funnelSubStepComplete() { },
    funnelSubStepError() { },
    helpPanelInteracted() { },
    externalLinkInteracted() { },
};
/**
 * This is a stub implementation of the PerformanceMetrics interface and will be replaced during
 * build time with the actual implementation.
 */
export let PerformanceMetrics = {
    tableInteraction() { },
    taskCompletionData() { },
    modalPerformanceData() { },
};
export let ComponentMetrics = {
    componentMounted() {
        return '';
    },
    componentUpdated() { },
};
//# sourceMappingURL=index.js.map