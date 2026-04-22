import { useContainerQuery } from '@cloudscape-design/component-toolkit';
export default function useContainerWidth(defaultValue = 0, threshold = 1) {
    const [width, ref] = useContainerQuery((rect, prev) => {
        if (prev === null) {
            return rect.contentBoxWidth;
        }
        return Math.abs(prev - rect.contentBoxWidth) >= threshold ? rect.contentBoxWidth : prev;
    });
    return [width !== null && width !== void 0 ? width : defaultValue, ref];
}
//# sourceMappingURL=use-container-width.js.map