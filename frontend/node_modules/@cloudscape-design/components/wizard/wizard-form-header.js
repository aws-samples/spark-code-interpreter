// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';
import clsx from 'clsx';
import { useVisualRefresh } from '../internal/hooks/use-visual-mode';
import styles from './styles.css.js';
export default function WizardFormHeader({ children }) {
    const isVisualRefresh = useVisualRefresh();
    return (React.createElement("div", { className: clsx(styles['form-header'], isVisualRefresh && styles['form-header-refresh']) },
        React.createElement("div", { className: styles['form-header-content'] }, children)));
}
//# sourceMappingURL=wizard-form-header.js.map