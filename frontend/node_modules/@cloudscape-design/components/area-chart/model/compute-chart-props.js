import { ChartScale, NumericChartScale } from '../../internal/components/cartesian-chart/scales';
import { createXTicks, createYTicks, getXTickCount, getYTickCount, } from '../../internal/components/cartesian-chart/ticks';
import { computeDomainX, computeDomainY, computePlotPoints } from './utils';
export default function computeChartProps({ isRtl, series, xDomain: externalXDomain, yDomain: externalYDomain, xScaleType, yScaleType, height, width, }) {
    const xDomain = externalXDomain ? [...externalXDomain] : computeDomainX(series);
    const xTickCount = getXTickCount(width);
    const xScale = new ChartScale(xScaleType, xDomain, !isRtl ? [0, width] : [width, 0]);
    const xTicks = xScale.domain.length > 0 ? createXTicks(xScale, xTickCount) : [];
    const yDomain = externalYDomain || computeDomainY(series, yScaleType);
    const yTickCount = getYTickCount(height);
    const yScale = new NumericChartScale(yScaleType, yDomain, [height, 0], externalYDomain ? null : yTickCount);
    const yTicks = createYTicks(yScale, yTickCount);
    const plot = computePlotPoints(series, xScale, yScale);
    return { xDomain, yDomain, xScale, yScale, xTicks, yTicks, plot };
}
//# sourceMappingURL=compute-chart-props.js.map