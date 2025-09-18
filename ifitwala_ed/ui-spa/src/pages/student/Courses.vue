<template>
  <div class="p-4 sm:p-6 lg:p-8">
    <div class="sm:flex sm:items-center sm:justify-between mb-6">
      <h1 class="text-2xl font-bold text-gray-900">My Courses</h1>
      <div v-if="!loading && academicYears.length" class="mt-4 sm:mt-0">
        <label for="academic-year" class="sr-only">Academic Year</label>
        <select
          id="academic-year"
          v-model="selectedYear"
          @change="fetchData"
          class="block w-full sm:w-auto pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
        >
          <option v-for="year in academicYears" :key="year" :value="year">
            {{ year }}
          </option>
        </select>
      </div>
    </div>

    <div v-if="loading" class="text-center py-10">
      <p class="text-gray-500">Loading courses...</p>
    </div>

    <div v-else-if="error" class="bg-red-50 border-l-4 border-red-400 p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <FeatherIcon name="alert-circle" class="h-5 w-5 text-red-400" />
        </div>
        <div class="ml-3">
          <p class="text-sm text-red-700">{{ error }}</p>
        </div>
      </div>
    </div>

    <div v-else-if="!courses.length" class="text-center py-10 border-2 border-dashed border-gray-300 rounded-lg">
      <p class="mt-2 text-sm text-gray-500">No courses found for the selected academic year.</p>
    </div>

    <div v-else class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      <RouterLink
        v-for="course in courses"
        :key="course.course"
        :to="course.href"
        class="group block bg-white rounded-lg shadow-md hover:shadow-xl transition-shadow duration-300 overflow-hidden"
      >
        <div class="relative">
          <div class="aspect-w-16 aspect-h-9">
            <img :src="course.course_image" :alt="course.course_name" class="object-cover w-full h-full" />
          </div>
        </div>
        <div class="p-4">
          <p class="text-base font-semibold text-gray-900 truncate group-hover:text-blue-600">
            {{ course.course_name }}
          </p>
          <p class="text-sm text-gray-500 mt-1">
            {{ course.course_group || '—' }}
          </p>
        </div>
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import { call } from 'frappe-ui';
import { FeatherIcon } from 'frappe-ui';

const loading = ref(true);
const error = ref(null);
const courses = ref([]);
const academicYears = ref([]);
const selectedYear = ref(null);

const fetchData = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await call({
      method: 'ifitwala_ed.api.courses.get_courses_data',
      args: {
        academic_year: selectedYear.value,
      },
    });

    if (response.message.error) {
      error.value = response.message.error;
      courses.value = [];
    } else {
      academicYears.value = response.message.academic_years;
      courses.value = response.message.courses;
      if (selectedYear.value === null) {
        selectedYear.value = response.message.selected_year;
      }
    }
  } catch (e) {
    error.value = 'An unexpected error occurred while fetching courses.';
    console.error(e);
  } finally {
    loading.value = false;
  }
};

onMounted(() => {
  fetchData();
});
</script>