// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';
import clsx from 'clsx';
import styles from './styles.css.js';
const ContentWrapper = React.forwardRef(({ className, style, contentType, children, toolsPadding, disablePaddings, navigationPadding, isMobile, contentWidthStyles, }, ref) => {
    if (disablePaddings) {
        return (React.createElement("div", { className: className, ref: ref, style: style }, children));
    }
    return (React.createElement("div", { ref: ref, className: clsx(styles['content-wrapper'], !navigationPadding && styles['content-wrapper-no-navigation-padding'], !toolsPadding && styles['content-wrapper-no-tools-padding'], isMobile && styles['content-wrapper-mobile']), style: style },
        React.createElement("div", { style: contentWidthStyles, className: clsx(className, styles[`content-type-${contentType}`]) }, children)));
});
export default ContentWrapper;
//# sourceMappingURL=index.js.map