// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import { createContext, useContext } from 'react';
export const FormFieldContext = createContext({});
function applyDefault(fields, defaults, keys) {
    const result = {};
    keys.forEach(key => {
        result[key] = fields[key] === undefined ? defaults[key] : fields[key];
    });
    return result;
}
export function useFormFieldContext(props) {
    const context = useContext(FormFieldContext);
    return applyDefault(props, context, ['invalid', 'warning', 'controlId', 'ariaLabelledby', 'ariaDescribedby']);
}
//# sourceMappingURL=form-field-context.js.map