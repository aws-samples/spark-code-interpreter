var _BreadcrumbsController_appLayoutUpdateCallback, _BreadcrumbsController_breadcrumbInstances, _BreadcrumbsController_breadcrumbRegistrations, _BreadcrumbsController_notifyAppLayout, _BreadcrumbsController_notifyBreadcrumbs;
import { __classPrivateFieldGet, __classPrivateFieldSet } from "tslib";
// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import debounce from '../../debounce';
export class BreadcrumbsController {
    constructor() {
        _BreadcrumbsController_appLayoutUpdateCallback.set(this, null);
        _BreadcrumbsController_breadcrumbInstances.set(this, []);
        _BreadcrumbsController_breadcrumbRegistrations.set(this, []);
        _BreadcrumbsController_notifyAppLayout.set(this, debounce(() => {
            var _a;
            if (!__classPrivateFieldGet(this, _BreadcrumbsController_appLayoutUpdateCallback, "f")) {
                return;
            }
            const latestBreadcrumb = __classPrivateFieldGet(this, _BreadcrumbsController_breadcrumbInstances, "f")[__classPrivateFieldGet(this, _BreadcrumbsController_breadcrumbInstances, "f").length - 1];
            __classPrivateFieldGet(this, _BreadcrumbsController_appLayoutUpdateCallback, "f").call(this, (_a = latestBreadcrumb === null || latestBreadcrumb === void 0 ? void 0 : latestBreadcrumb.props) !== null && _a !== void 0 ? _a : null);
        }, 0));
        _BreadcrumbsController_notifyBreadcrumbs.set(this, debounce(() => {
            __classPrivateFieldGet(this, _BreadcrumbsController_breadcrumbRegistrations, "f").forEach(listener => listener(!!__classPrivateFieldGet(this, _BreadcrumbsController_appLayoutUpdateCallback, "f")));
        }, 0));
        this.registerAppLayout = (changeCallback) => {
            if (__classPrivateFieldGet(this, _BreadcrumbsController_appLayoutUpdateCallback, "f")) {
                return;
            }
            __classPrivateFieldSet(this, _BreadcrumbsController_appLayoutUpdateCallback, changeCallback, "f");
            __classPrivateFieldGet(this, _BreadcrumbsController_notifyBreadcrumbs, "f").call(this);
            return () => {
                __classPrivateFieldSet(this, _BreadcrumbsController_appLayoutUpdateCallback, null, "f");
                __classPrivateFieldGet(this, _BreadcrumbsController_notifyBreadcrumbs, "f").call(this);
            };
        };
        this.registerBreadcrumbs = (props, onRegistered) => {
            const instance = { props: props };
            __classPrivateFieldGet(this, _BreadcrumbsController_breadcrumbInstances, "f").push(instance);
            __classPrivateFieldGet(this, _BreadcrumbsController_breadcrumbRegistrations, "f").push(onRegistered);
            __classPrivateFieldGet(this, _BreadcrumbsController_notifyBreadcrumbs, "f").call(this);
            __classPrivateFieldGet(this, _BreadcrumbsController_notifyAppLayout, "f").call(this);
            return {
                update: props => {
                    instance.props = props;
                    __classPrivateFieldGet(this, _BreadcrumbsController_notifyAppLayout, "f").call(this);
                },
                cleanup: () => {
                    __classPrivateFieldGet(this, _BreadcrumbsController_breadcrumbInstances, "f").splice(__classPrivateFieldGet(this, _BreadcrumbsController_breadcrumbInstances, "f").indexOf(instance), 1);
                    __classPrivateFieldGet(this, _BreadcrumbsController_breadcrumbRegistrations, "f").splice(__classPrivateFieldGet(this, _BreadcrumbsController_breadcrumbRegistrations, "f").indexOf(onRegistered), 1);
                    __classPrivateFieldGet(this, _BreadcrumbsController_notifyAppLayout, "f").call(this);
                },
            };
        };
        this.getStateForTesting = () => {
            return {
                appLayoutUpdateCallback: __classPrivateFieldGet(this, _BreadcrumbsController_appLayoutUpdateCallback, "f"),
                breadcrumbInstances: __classPrivateFieldGet(this, _BreadcrumbsController_breadcrumbInstances, "f"),
                breadcrumbRegistrations: __classPrivateFieldGet(this, _BreadcrumbsController_breadcrumbRegistrations, "f"),
            };
        };
    }
    installInternal(internalApi = {}) {
        var _a, _b, _c;
        (_a = internalApi.registerBreadcrumbs) !== null && _a !== void 0 ? _a : (internalApi.registerBreadcrumbs = this.registerBreadcrumbs);
        (_b = internalApi.registerAppLayout) !== null && _b !== void 0 ? _b : (internalApi.registerAppLayout = this.registerAppLayout);
        (_c = internalApi.getStateForTesting) !== null && _c !== void 0 ? _c : (internalApi.getStateForTesting = this.getStateForTesting);
        return internalApi;
    }
}
_BreadcrumbsController_appLayoutUpdateCallback = new WeakMap(), _BreadcrumbsController_breadcrumbInstances = new WeakMap(), _BreadcrumbsController_breadcrumbRegistrations = new WeakMap(), _BreadcrumbsController_notifyAppLayout = new WeakMap(), _BreadcrumbsController_notifyBreadcrumbs = new WeakMap();
//# sourceMappingURL=breadcrumbs.js.map