const variantIsOneOf = (variant, oneOf) => oneOf.includes(variant);
export function variantSupportsDescription(variant) {
    return variantIsOneOf(variant, ['container', 'default', 'footer', 'inline']);
}
export function variantSupportsActions(variant) {
    return variantIsOneOf(variant, ['container', 'compact', 'default', 'inline']);
}
export function variantSupportsInfoLink(variant) {
    return variantIsOneOf(variant, ['container', 'compact']);
}
export function variantRequiresActionsDivider(variant) {
    return variantIsOneOf(variant, ['default', 'inline']);
}
//# sourceMappingURL=utils.js.map