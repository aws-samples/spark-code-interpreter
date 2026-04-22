// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { createContext, useContext } from 'react';
const ContainerHeaderContext = createContext({ isInContainer: false });
export const ContainerHeaderContextProvider = ({ children }) => {
    return React.createElement(ContainerHeaderContext.Provider, { value: { isInContainer: true } }, children);
};
export const useContainerHeader = () => {
    const { isInContainer } = useContext(ContainerHeaderContext);
    return isInContainer;
};
//# sourceMappingURL=container-header.js.map