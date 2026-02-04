// ifitwala_ed/ui-spa/src/lib/echarts.ts

import { use } from 'echarts/core'

// Charts you actually need
import { BarChart, HeatmapChart, LineChart, PieChart } from 'echarts/charts'

// Components (grid, tooltip, legend, title, etc.)
import {
	GridComponent,
	TooltipComponent,
	LegendComponent,
	TitleComponent,
	VisualMapComponent,
} from 'echarts/components'

// Renderer
import { CanvasRenderer } from 'echarts/renderers'

// Register with ECharts' core
use([
	CanvasRenderer,
	BarChart,
	HeatmapChart,
	LineChart,
	PieChart,
	GridComponent,
	TooltipComponent,
	LegendComponent,
	TitleComponent,
	VisualMapComponent,
])

// Re-export type & helpers for convenience
export type { ComposeOption } from 'echarts/core'
export type { BarSeriesOption, HeatmapSeriesOption, LineSeriesOption, PieSeriesOption } from 'echarts/charts'
export type {
	TooltipComponentOption,
	LegendComponentOption,
	TitleComponentOption,
	GridComponentOption,
	VisualMapComponentOption,
} from 'echarts/components'

export { default as VChart, THEME_KEY } from 'vue-echarts'
