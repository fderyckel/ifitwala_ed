<template>
  <div class="flex flex-col gap-6 p-6">
    <header class="flex items-center justify-between">
      <h1 class="text-3xl font-bold text-slate-900">Inquiry Analytics</h1>
      <button 
        class="rounded bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-800"
        @click="refresh"
      >
        Refresh
      </button>
    </header>

    <FiltersBar>
      <div class="flex flex-col gap-1">
        <label class="text-xs font-medium text-slate-500">Academic Year</label>
        <select 
          v-model="filters.academic_year" 
          class="h-9 rounded-md border border-slate-300 bg-transparent px-2 text-sm outline-none focus:border-slate-900"
        >
          <option value="">All Years</option>
          <option v-for="y in academicYears" :key="y" :value="y">{{ y }}</option>
        </select>
      </div>

      <div class="flex flex-col gap-1">
        <label class="text-xs font-medium text-slate-500">Date Range (Submitted)</label>
        <div class="flex items-center gap-2">
          <input 
            type="date" 
            v-model="filters.from_date"
            class="h-9 rounded-md border border-slate-300 bg-transparent px-2 text-sm outline-none focus:border-slate-900"
          />
          <span class="text-slate-400">-</span>
          <input 
            type="date" 
            v-model="filters.to_date"
            class="h-9 rounded-md border border-slate-300 bg-transparent px-2 text-sm outline-none focus:border-slate-900"
          />
        </div>
      </div>

      <div class="flex flex-col gap-1">
        <label class="text-xs font-medium text-slate-500">Assignee</label>
        <select 
          v-model="filters.assigned_to"
          class="h-9 min-w-[140px] rounded-md border border-slate-300 bg-transparent px-2 text-sm outline-none focus:border-slate-900"
        >
          <option value="">All Users</option>
          <option v-for="u in users" :key="u.name" :value="u.name">{{ u.full_name }}</option>
        </select>
      </div>

      <div class="flex flex-col gap-1">
        <label class="text-xs font-medium text-slate-500">Inquiry Type</label>
        <select 
          v-model="filters.type_of_inquiry"
          class="h-9 min-w-[140px] rounded-md border border-slate-300 bg-transparent px-2 text-sm outline-none focus:border-slate-900"
        >
          <option value="">All Types</option>
          <option v-for="t in inquiryTypes" :key="t" :value="t">{{ t }}</option>
        </select>
      </div>
    </FiltersBar>

    <div v-if="loading" class="py-12 text-center text-slate-500">
      Loading analytics...
    </div>

    <template v-else>
      <KpiRow :items="kpiItems" />

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <!-- Pipeline -->
        <HorizontalBarTopN
          title="Pipeline by State"
          :items="pipelineItems"
        />

        <!-- Weekly Volume -->
        <section class="flex flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 class="mb-4 text-sm font-bold text-slate-700">Weekly Volume</h3>
          <AnalyticsChart :option="weeklyChartOption" />
        </section>
      </div>

      <div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <HorizontalBarTopN
          title="Assigned To"
          :items="assigneeItems"
        />
        <HorizontalBarTopN
          title="Inquiry Types"
          :items="typeItems"
        />
      </div>

      <!-- Detailed Stats & Trends -->
      <section class="grid grid-cols-1 gap-6 lg:grid-cols-3">
        
        <!-- SLA & Response Stats -->
        <div class="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
           <h3 class="text-sm font-bold text-slate-700">Performance Metrics</h3>
           <div class="flex flex-wrap gap-3">
             <StatsTile 
               label="SLA Compliance (30d)" 
               :value="data?.sla?.pct_30d + '%'" 
               :tone="slaTone"
             />
             <StatsTile 
               label="First Response (Avg)" 
               :value="data?.averages?.overall?.first_contact_hours + 'h'" 
             />
             <StatsTile 
               label="From Assign (Avg)" 
               :value="data?.averages?.overall?.from_assign_hours + 'h'" 
             />
           </div>
           
           <h4 class="mt-2 text-xs font-semibold text-slate-500 uppercase tracking-wider">Last 30 Days</h4>
           <div class="flex gap-4 text-sm">
             <div class="flex flex-col">
               <span class="text-slate-500">First Contact</span>
               <span class="font-medium">{{ data?.averages?.last30d?.first_contact_hours }}h</span>
             </div>
             <div class="flex flex-col">
               <span class="text-slate-500">From Assign</span>
               <span class="font-medium">{{ data?.averages?.last30d?.from_assign_hours }}h</span>
             </div>
           </div>
        </div>

        <!-- Monthly Trends -->
        <div class="col-span-2 flex flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h3 class="mb-4 text-sm font-bold text-slate-700">Monthly Average Response Time (Hours)</h3>
          <AnalyticsChart :option="monthlyChartOption" />
        </div>
      </section>

    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { getInquiryDashboardData, getInquiryTypes, searchAdmissionUsers, searchAcademicYears } from '@/api/admission'
import FiltersBar from '@/components/analytics/FiltersBar.vue'
import KpiRow from '@/components/analytics/KpiRow.vue'
import StatsTile from '@/components/analytics/StatsTile.vue'
import AnalyticsChart from '@/components/analytics/AnalyticsChart.vue'
import HorizontalBarTopN from '@/components/analytics/HorizontalBarTopN.vue'

// -- State --
const loading = ref(false)
const data = ref<any>(null)

const filters = ref({
  academic_year: '',
  from_date: '',
  to_date: '',
  assigned_to: '',
  type_of_inquiry: '',
  sla_status: '',
})

// Options
const inquiryTypes = ref<string[]>([])
const users = ref<{name: string, full_name: string}[]>([])
const academicYears = ref<string[]>([])

// -- Actions --
async function loadOptions() {
  const [types, userList, years] = await Promise.all([
    getInquiryTypes(),
    searchAdmissionUsers(''),
    searchAcademicYears('')
  ])
  inquiryTypes.value = types || []
  if (userList) users.value = userList.map((u: any) => ({ name: u[0], full_name: u[1] }))
  if (years) academicYears.value = years.map((y: any) => y[0])
}

async function refresh() {
  loading.value = true
  try {
    const res = await getInquiryDashboardData(filters.value)
    data.value = res
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

watch(filters, () => {
  // simple debounce could be added here
  refresh()
}, { deep: true })

onMounted(async () => {
  await loadOptions()
  refresh()
})

// -- Computed View Models --

const kpiItems = computed(() => {
  if (!data.value) return []
  const c = data.value.counts
  return [
    { id: 'total', label: 'Total Inquiries', value: c.total },
    { id: 'contacted', label: 'Contacted', value: c.contacted },
    { id: 'overdue', label: 'Overdue First Contact', value: c.overdue_first_contact, hint: 'Action Needed' },
    { id: 'due_today', label: 'Due Today', value: c.due_today },
    { id: 'upcoming', label: 'Upcoming', value: c.upcoming, hint: `Next ${data.value.config?.upcoming_horizon_days || 7} Days` },
  ]
})

const pipelineItems = computed(() => {
  if (!data.value?.pipeline_by_state) return []
  return data.value.pipeline_by_state.map((d: any) => ({
    label: d.label,
    count: d.value,
  }))
})

const assigneeItems = computed(() => {
  if (!data.value?.assignee_distribution) return []
  return data.value.assignee_distribution.map((d: any) => ({
    label: d.label, // This is the ID/Email usually, ideally we map it to full name if possible, but backend sends ID
    count: d.value,
  }))
})

const typeItems = computed(() => {
  if (!data.value?.type_distribution) return []
  return data.value.type_distribution.map((d: any) => ({
    label: d.label,
    count: d.value,
    pct: data.value.counts.total ? Math.round((d.value / data.value.counts.total) * 100) : 0
  }))
})

const slaTone = computed(() => {
  const pct = data.value?.sla?.pct_30d || 0
  if (pct >= 90) return 'success'
  if (pct >= 70) return 'info'
  return 'warning'
})

// -- Charts --

const weeklyChartOption = computed(() => {
  const s = data.value?.weekly_volume_series
  if (!s) return {}
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: 40, right: 20, top: 20, bottom: 20, containLabel: true },
    xAxis: { type: 'category', data: s.labels, axisLabel: { color: '#64748b' } },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } } },
    series: [
      {
        data: s.values,
        type: 'line',
        smooth: true,
        areaStyle: { opacity: 0.1 },
        itemStyle: { color: '#3b82f6' },
      }
    ]
  }
})

const monthlyChartOption = computed(() => {
  const s = data.value?.monthly_avg_series
  if (!s) return {}
  return {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    grid: { left: 40, right: 20, top: 20, bottom: 40, containLabel: true },
    xAxis: { type: 'category', data: s.labels, axisLabel: { color: '#64748b' } },
    yAxis: { type: 'value', splitLine: { lineStyle: { type: 'dashed' } }, name: 'Hours' },
    series: [
      {
        name: 'First Contact',
        data: s.first_contact,
        type: 'bar',
        itemStyle: { color: '#8b5cf6' },
      },
      {
        name: 'From Assign',
        data: s.from_assign,
        type: 'bar',
        itemStyle: { color: '#10b981' },
      }
    ]
  }
})

</script>
