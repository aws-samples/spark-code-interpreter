var _AppLayoutWidgetController_registrations, _AppLayoutWidgetController_findPrimary, _AppLayoutWidgetController_update, _AppLayoutWidgetController_scheduleUpdate;
import { __classPrivateFieldGet } from "tslib";
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import debounce from '../../debounce';
export class AppLayoutWidgetController {
    constructor() {
        _AppLayoutWidgetController_registrations.set(this, []);
        _AppLayoutWidgetController_findPrimary.set(this, () => {
            const forcedPrimary = __classPrivateFieldGet(this, _AppLayoutWidgetController_registrations, "f").find(registration => registration.forceType === 'primary');
            if (forcedPrimary) {
                return forcedPrimary;
            }
            for (const registration of __classPrivateFieldGet(this, _AppLayoutWidgetController_registrations, "f").slice()) {
                if (registration.forceType !== 'secondary') {
                    return registration;
                }
            }
            return undefined;
        });
        _AppLayoutWidgetController_update.set(this, () => {
            const primary = __classPrivateFieldGet(this, _AppLayoutWidgetController_findPrimary, "f").call(this);
            const discoveredProps = __classPrivateFieldGet(this, _AppLayoutWidgetController_registrations, "f")
                .filter(registration => registration !== primary)
                .map(registration => registration.props);
            for (const registration of __classPrivateFieldGet(this, _AppLayoutWidgetController_registrations, "f")) {
                if (registration === primary) {
                    registration.onChange({
                        type: 'primary',
                        discoveredProps,
                    });
                }
                else {
                    registration.onChange(registration.secondaryInstance);
                }
            }
        });
        _AppLayoutWidgetController_scheduleUpdate.set(this, debounce(() => __classPrivateFieldGet(this, _AppLayoutWidgetController_update, "f").call(this), 0));
        this.register = (forceType, onRegistrationChange) => {
            const hasForcedPrimary = __classPrivateFieldGet(this, _AppLayoutWidgetController_registrations, "f").some(instance => instance.forceType === 'primary');
            if (forceType === 'primary' && hasForcedPrimary) {
                throw new Error('Double primary registration attempt');
            }
            const registration = {
                forceType,
                onChange: onRegistrationChange,
                props: {},
                secondaryInstance: {
                    type: 'secondary',
                    update: props => {
                        registration.props = props;
                        __classPrivateFieldGet(this, _AppLayoutWidgetController_scheduleUpdate, "f").call(this);
                    },
                },
            };
            __classPrivateFieldGet(this, _AppLayoutWidgetController_registrations, "f").push(registration);
            __classPrivateFieldGet(this, _AppLayoutWidgetController_update, "f").call(this);
            return () => {
                __classPrivateFieldGet(this, _AppLayoutWidgetController_registrations, "f").splice(__classPrivateFieldGet(this, _AppLayoutWidgetController_registrations, "f").indexOf(registration), 1);
                __classPrivateFieldGet(this, _AppLayoutWidgetController_scheduleUpdate, "f").call(this);
            };
        };
        this.getStateForTesting = () => {
            return {
                registrations: __classPrivateFieldGet(this, _AppLayoutWidgetController_registrations, "f"),
            };
        };
        this.installInternal = (internalApi = {}) => {
            var _a, _b;
            (_a = internalApi.register) !== null && _a !== void 0 ? _a : (internalApi.register = this.register);
            (_b = internalApi.getStateForTesting) !== null && _b !== void 0 ? _b : (internalApi.getStateForTesting = this.getStateForTesting);
            return internalApi;
        };
    }
}
_AppLayoutWidgetController_registrations = new WeakMap(), _AppLayoutWidgetController_findPrimary = new WeakMap(), _AppLayoutWidgetController_update = new WeakMap(), _AppLayoutWidgetController_scheduleUpdate = new WeakMap();
//# sourceMappingURL=app-layout-widget.js.map