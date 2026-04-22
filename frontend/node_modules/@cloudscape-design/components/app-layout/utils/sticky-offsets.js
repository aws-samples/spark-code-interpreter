// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import globalVars from '../../internal/styles/global-vars';
export function getStickyOffsetVars(headerHeight, footerHeight, stickyNotificationsHeight, mobileToolbarHeight, disableBodyScroll, isMobile) {
    return {
        [globalVars.stickyVerticalTopOffset]: `calc(${!disableBodyScroll ? headerHeight : 0}px + ${isMobile ? mobileToolbarHeight : stickyNotificationsHeight})`,
        [globalVars.stickyVerticalBottomOffset]: `${!disableBodyScroll ? footerHeight : 0}px`,
    };
}
//# sourceMappingURL=sticky-offsets.js.map