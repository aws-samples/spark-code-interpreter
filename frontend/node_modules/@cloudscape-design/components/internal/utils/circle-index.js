// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
// Returns given index if it is in range or the opposite range boundary otherwise.
export function circleIndex(index, [from, to]) {
    if (index < from) {
        return to;
    }
    if (index > to) {
        return from;
    }
    return index;
}
//# sourceMappingURL=circle-index.js.map