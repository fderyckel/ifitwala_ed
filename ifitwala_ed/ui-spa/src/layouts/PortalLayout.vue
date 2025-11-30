<!-- ifitwala_ed/ifitwala_ed/ui-spa/src/layouts/PortalLayout.vue -->
<template>
	<!-- Soft jacaranda / sky / sand gradient on the whole portal -->
	<div
		class="min-h-screen flex flex-col text-ink
		       bg-gradient-to-b from-sky/95 via-sand/95 to-white
		       bg-[radial-gradient(circle_at_0_0,rgba(var(--jacaranda-rgb),0.18),transparent_55%)]
		       sm:bg-[radial-gradient(circle_at_0_0,rgba(var(--jacaranda-rgb),0.18),transparent_55%),radial-gradient(circle_at_100%_0,rgba(var(--leaf-rgb),0.14),transparent_55%),linear-gradient(to_bottom,rgba(var(--sky-rgb),0.98),rgba(var(--sand-rgb),0.98))]"
	>
		<PortalNavbar @toggle-sidebar="toggleSidebar" />

		<div class="flex flex-1">
			<PortalSidebar :is-open="isSidebarOpen" @close="isSidebarOpen = false" />

			<!-- Main content column sits on a faint card to stand off the gradient -->
			<div class="flex-1 flex flex-col">
				<main
					class="flex-1 px-4 py-4 sm:px-6 sm:py-6 lg:px-8 lg:py-8 pb-[var(--footer-h)]
					       bg-[#fcfbf9]/75 backdrop-blur-sm shadow-[0_10px_35px_rgba(7,16,25,0.10)]
					       sm:m-4 sm:rounded-3xl sm:border sm:border-sand-200"
				>
					<slot />
				</main>

				<PortalFooter />
			</div>
		</div>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import PortalNavbar from '../components/PortalNavbar.vue'
import PortalSidebar from '../components/PortalSidebar.vue'
import PortalFooter from '../components/PortalFooter.vue'

const isSidebarOpen = ref(false)

const toggleSidebar = () => {
  isSidebarOpen.value = !isSidebarOpen.value
}
</script>
