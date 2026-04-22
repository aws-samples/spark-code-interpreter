// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import analyticsSelectors from './styles.css.js';
export const getComponentsAnalyticsMetadata = (itemsCount, stackItems, expanded) => {
    const metadata = {
        component: {
            name: 'awsui.Flashbar',
            label: stackItems ? { root: 'self', selector: 'ul' } : { root: 'self' },
            properties: {
                itemsCount: `${itemsCount}`,
                stackItems: `${stackItems}`,
            },
        },
    };
    if (expanded !== undefined) {
        metadata.component.properties.expanded = `${expanded}`;
    }
    return metadata;
};
export const getItemAnalyticsMetadata = (position, type, id) => {
    const baseMetadata = {
        itemLabel: `.${analyticsSelectors['flash-header']}`,
        itemPosition: `${position}`,
        itemType: type,
    };
    if (id) {
        baseMetadata.itemId = id;
    }
    return {
        component: { innerContext: baseMetadata },
    };
};
//# sourceMappingURL=utils.js.map