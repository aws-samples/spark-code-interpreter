// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import { getAnalyticsMetadataAttribute, } from '@cloudscape-design/component-toolkit/internal/analytics-metadata';
export const getNavigationActionDetail = (targetStepIndex, reason, addAction = false, label) => {
    const metadata = { detail: { targetStepIndex: `${targetStepIndex}`, reason } };
    if (addAction) {
        metadata.action = 'navigate';
    }
    if (label) {
        metadata.detail.label = label;
    }
    return getAnalyticsMetadataAttribute(metadata);
};
//# sourceMappingURL=utils.js.map