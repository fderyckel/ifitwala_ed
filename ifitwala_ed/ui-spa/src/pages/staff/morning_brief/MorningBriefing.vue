<template>
  <div class="min-h-screen bg-transparent p-4 sm:p-6 space-y-8">

    <header class="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <h1 class="text-3xl font-bold tracking-tight text-heading">Morning Briefing</h1>
        <p class="text-slate-500 mt-1 font-medium">Daily Operational & Academic Pulse</p>
      </div>
      <div class="flex items-center gap-3">
        <div class="text-right">
          <span class="section-header block mb-0.5">Today</span>
          <span class="text-lg font-semibold text-ink">{{ formattedDate }}</span>
        </div>
        <button @click="widgets.reload()" class="remark-btn flex items-center justify-center ml-2">
          <FeatherIcon name="refresh-cw" class="h-4 w-4" :class="{ 'animate-spin': widgets.loading }" />
        </button>
      </div>
    </header>

    <div v-if="widgets.loading" class="animate-pulse space-y-6">
      <div class="h-40 bg-slate-100 rounded-2xl w-full"></div>
      <div class="grid grid-cols-3 gap-6">
        <div class="col-span-2 h-64 bg-slate-100 rounded-2xl"></div>
        <div class="h-64 bg-slate-100 rounded-2xl"></div>
      </div>
    </div>

    <div v-else class="space-y-8">

      <section v-if="hasData('announcements')" class="w-full grid gap-4">

         <div v-for="(news, idx) in widgets.data.announcements" :key="idx"
              class="relative overflow-hidden rounded-2xl p-6 shadow-sm transition-all"
              :class="getPriorityClasses(news.priority)"
         >
            <div v-if="news.priority !== 'Critical'" class="absolute inset-0 bg-gradient-to-r from-jacaranda to-purple-800 opacity-100 z-0"></div>
            <div v-if="news.priority !== 'Critical'" class="absolute top-0 right-0 -mt-4 -mr-4 h-32 w-32 bg-white/10 rounded-full blur-2xl z-0"></div>

            <div class="relative z-10">
              <div class="flex justify-between items-start mb-2">
                 <div class="flex gap-2">
                    <span class="inline-flex items-center gap-1 rounded-md bg-white/20 px-2 py-1 text-xs font-medium text-white ring-1 ring-inset ring-white/30">
                       <FeatherIcon :name="getIconForType(news.type)" class="h-3 w-3" />
                       {{ news.type }}
                    </span>
                    <span v-if="news.priority === 'Critical'" class="inline-flex items-center gap-1 rounded-md bg-red-100 px-2 py-1 text-xs font-bold text-red-700">
                       CRITICAL
                    </span>
                 </div>
              </div>

              <h3 class="text-lg font-bold text-white mb-2">{{ news.title }}</h3>

              <div class="prose prose-sm prose-invert max-w-none text-white/90 leading-relaxed" v-html="news.content"></div>
            </div>
         </div>
      </section>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

        <div class="lg:col-span-8 space-y-6">

           <section v-if="hasData('clinic_volume') || hasData('admissions_pulse') || widgets.data?.critical_incidents !== undefined">
              <h2 class="section-header mb-4 flex items-center gap-2">Operational Health</h2>
              <div class="grid grid-cols-1 md:grid-cols-3 gap-6">

                 <div v-if="widgets.data?.critical_incidents !== undefined" class="paper-card p-5 border-l-4 border-l-flame">
                    <h3 class="section-header !text-flame/80 mb-1">Critical Incidents</h3>
                    <div class="text-3xl font-bold text-ink">{{ widgets.data.critical_incidents }}</div>
                    <p class="text-xs text-flame mt-1 font-medium flex items-center gap-1">
                       <FeatherIcon name="alert-circle" class="h-3 w-3" /> Open Follow-ups
                    </p>
                 </div>

                 <div v-if="hasData('clinic_volume')" class="paper-card p-5">
                    <div class="flex items-center gap-2 mb-3">
                       <div class="h-8 w-8 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center">
                          <FeatherIcon name="thermometer" class="h-4 w-4" />
                       </div>
                       <h3 class="font-semibold text-canopy text-sm">Clinic Volume</h3>
                    </div>
                    <div class="space-y-2">
                       <div v-for="day in widgets.data.clinic_volume" :key="day.date" class="flex justify-between items-center text-sm">
                          <span class="text-slate-500">{{ day.date }}</span>
                          <span class="font-mono font-medium" :class="day.count > 10 ? 'text-flame' : 'text-ink'">{{ day.count }}</span>
                       </div>
                    </div>
                 </div>

                 <div v-if="widgets.data?.admissions_pulse" class="paper-card p-5">
                    <div class="flex items-center justify-between mb-3">
                       <div class="flex items-center gap-2">
                          <div class="h-8 w-8 rounded-full bg-purple-50 text-purple-600 flex items-center justify-center">
                             <FeatherIcon name="users" class="h-4 w-4" />
                          </div>
                          <h3 class="font-semibold text-canopy text-sm">Admissions</h3>
                       </div>
                       <span class="text-2xl font-bold text-ink">{{ widgets.data.admissions_pulse.total_new_weekly }}</span>
                    </div>
                    <div class="flex flex-wrap gap-2">
                       <div v-for="stat in widgets.data.admissions_pulse.breakdown" :key="stat.application_status" class="inline-chip bg-slate-100 text-slate-600 border border-slate-200">
                          {{ stat.application_status }}: {{ stat.count }}
                       </div>
                    </div>
                 </div>
              </div>
           </section>

           <section v-if="hasData('medical_context') || widgets.data?.grading_velocity !== undefined">
              <h2 class="section-header mb-4 flex items-center gap-2">Classroom Context</h2>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                 <div v-if="widgets.data?.grading_velocity !== undefined" class="paper-card p-5 border-l-4 border-l-clay">
                    <h3 class="section-header !text-clay/80 mb-1">Pending Grading</h3>
                    <div class="mt-2 flex items-baseline gap-2">
                       <span class="text-3xl font-bold text-ink">{{ widgets.data.grading_velocity }}</span>
                       <span class="text-sm text-slate-500">tasks overdue</span>
                    </div>
                 </div>

                 <div v-if="hasData('medical_context')" class="paper-card p-5 border-l-4 border-l-sky">
                    <h3 class="font-semibold text-canopy text-sm mb-3">Medical Alerts</h3>
                    <div class="space-y-2 max-h-32 overflow-y-auto custom-scrollbar">
                       <div v-for="med in widgets.data.medical_context" :key="med.first_name" class="text-sm">
                          <span class="font-bold text-ink">{{ med.first_name }}:</span>
                          <span class="text-slate-600 ml-1">{{ med.food_allergies || 'See info' }}</span>
                       </div>
                    </div>
                 </div>
              </div>
           </section>
        </div>

        <div class="lg:col-span-4" v-if="hasData('student_logs')">
           <h2 class="section-header mb-4 flex items-center gap-2 text-flame">
              <FeatherIcon name="clipboard" class="h-3 w-3" />
              Recent Logs (48h)
           </h2>

           <div class="paper-card flex flex-col max-h-[600px] relative">
              <div class="overflow-y-auto p-0 custom-scrollbar">
                 <div v-for="(log, i) in widgets.data.student_logs" :key="log.name"
                      class="p-4 border-b border-border/50 last:border-0 hover:bg-slate-50 transition-colors group cursor-pointer">

                    <div class="flex gap-3">
                       <div class="flex-shrink-0 relative">
                          <div class="h-10 w-10 rounded-xl bg-slate-200 overflow-hidden">
                             <img v-if="log.student_photo" :src="log.student_photo" class="h-full w-full object-cover">
                             <div v-else class="h-full w-full flex items-center justify-center text-xs font-bold text-slate-500">
                                {{ log.student_name.substring(0,2) }}
                             </div>
                          </div>
                          <div v-if="log.status_color === 'red'" class="absolute -top-1 -right-1 h-3 w-3 bg-flame rounded-full ring-2 ring-white"></div>
                          <div v-else-if="log.status_color === 'green'" class="absolute -top-1 -right-1 h-3 w-3 bg-leaf rounded-full ring-2 ring-white"></div>
                       </div>

                       <div class="flex-1 min-w-0">
                          <div class="flex justify-between items-start">
                             <h4 class="text-sm font-bold text-ink truncate">{{ log.student_name }}</h4>
                             <span class="text-[10px] text-slate-400 whitespace-nowrap">{{ log.date_display }}</span>
                          </div>

                          <div class="flex items-center gap-2 mt-0.5 mb-1">
                             <span class="text-[10px] uppercase font-semibold text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                                {{ log.log_type }}
                             </span>
                          </div>

                          <p class="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                             {{ log.snippet }}
                          </p>
                       </div>
                    </div>
                 </div>
              </div>
           </div>
        </div>

      </div>

      <section v-if="hasData('staff_birthdays')">
         <div class="border-t border-border/60 pt-6">
            <h2 class="section-header mb-4 flex items-center gap-2 text-slate-400">
               <FeatherIcon name="gift" class="h-3 w-3" />
               Community Pulse
            </h2>
            <div class="flex flex-wrap gap-4 items-center">
               <div v-for="emp in widgets.data.staff_birthdays" :key="emp.name"
                    class="flex items-center gap-2 bg-white border border-border/80 rounded-full pr-4 p-1 shadow-sm">
                  <div class="h-8 w-8 rounded-full bg-slate-100 overflow-hidden">
                     <img v-if="emp.image" :src="emp.image" class="h-full w-full object-cover" />
                     <div v-else class="h-full w-full flex items-center justify-center text-xs font-bold text-slate-400">
                        {{ emp.name.substring(0,1) }}
                     </div>
                  </div>
                  <div class="flex flex-col">
                     <span class="text-xs font-bold text-ink">{{ emp.name }}</span>
                     <span class="text-[10px] text-amber-600 font-medium uppercase">{{ emp.birthday_display }}</span>
                  </div>
               </div>
            </div>
         </div>
      </section>

    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { createResource, FeatherIcon } from 'frappe-ui'

const widgets = createResource({
  url: 'ifitwala_ed.api.morning_brief.get_briefing_widgets',
  auto: true
})

function hasData(key) {
  return widgets.data && widgets.data[key] && Array.isArray(widgets.data[key]) && widgets.data[key].length > 0
}

const formattedDate = computed(() => {
  const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
  return new Date().toLocaleDateString('en-GB', options);
})

function getPriorityClasses(priority) {
  if (priority === 'Critical') {
    return 'bg-red-600 text-white ring-4 ring-red-100'
  }
  // Default gradient handled in template
  return ''
}

function getIconForType(type) {
  const map = {
    'Logistics': 'truck',
    'Alert': 'bell',
    'Celebration': 'award',
    'Urgent': 'zap',
    'Policy Procedure': 'file-text'
  }
  return map[type] || 'info'
}
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 4px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 20px;
}
</style>
