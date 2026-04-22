// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';
import InternalLiveRegion from '../live-region/internal';
import styles from './styles.css.js';
export const AdditionalInfo = ({ children, id }) => (React.createElement(InternalLiveRegion, { "data-testid": "info-live-region" },
    React.createElement("div", { id: id, className: styles['additional-info'] }, children)));
//# sourceMappingURL=additional-info.js.map