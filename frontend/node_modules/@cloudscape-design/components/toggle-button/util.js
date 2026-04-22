// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
export function getToggleIcon(pressed, defaultIcon, pressedIcon) {
    if (pressed) {
        return pressedIcon !== null && pressedIcon !== void 0 ? pressedIcon : defaultIcon;
    }
    return defaultIcon;
}
//# sourceMappingURL=util.js.map