<template>
	<!--
  PortalNotification.vue
  Global notification toast component that listens to socket events.
  Displays system-wide alerts or messages.

  Used by:
  - PortalLayout.vue
-->
	<Transition
		enter-active-class="transform ease-out duration-300 transition"
		enter-from-class="translate-y-2 opacity-0 sm:translate-y-0 sm:translate-x-2"
		enter-to-class="translate-y-0 opacity-100 sm:translate-x-0"
		leave-active-class="transition ease-in duration-100"
		leave-from-class="opacity-100"
		leave-to-class="opacity-0"
	>
		<div
			v-if="visible"
			class="pointer-events-auto w-full max-w-sm overflow-hidden rounded-lg bg-white shadow-lg ring-1 ring-black ring-opacity-5 fixed bottom-4 right-4 z-50 cursor-pointer"
			@click.stop="close"
		>
			<div class="p-4">
				<div class="flex items-start">
					<div class="flex-shrink-0" v-if="notification.image">
						<img class="h-10 w-10 rounded-full object-cover" :src="notification.image" alt="" />
					</div>
					<div class="flex-shrink-0" v-else-if="notification.icon">
						<component :is="notification.icon" class="h-6 w-6 text-gray-400" aria-hidden="true" />
					</div>
					<div class="ml-3 w-0 flex-1 pt-0.5">
						<p class="text-sm font-medium text-gray-900">{{ notification.title }}</p>
						<p class="mt-1 text-sm text-gray-500">{{ notification.content }}</p>
					</div>
					<div class="ml-4 flex flex-shrink-0">
						<button
							type="button"
							class="inline-flex rounded-md bg-white text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:ring-offset-2"
							@click.stop="close"
						>
							<span class="sr-only">Close</span>
							<FeatherIcon name="x" class="h-5 w-5" aria-hidden="true" />
						</button>
					</div>
				</div>
			</div>
			<div class="bg-gray-50 px-4 py-2 text-xs text-gray-500 italic">
				Click anywhere to dismiss
			</div>
		</div>
	</Transition>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { FeatherIcon } from 'frappe-ui';
import { socket } from '../lib/socket';

interface Notification {
	title: string;
	content: string;
	image?: string;
	icon?: any;
	type?: 'info' | 'warning' | 'success' | 'error';
}

const visible = ref(false);
const notification = ref<Notification>({ title: '', content: '' });

const close = () => {
	visible.value = false;
	window.removeEventListener('click', close);
};

const show = (data: any) => {
	notification.value = {
		title: data.title || 'Notification',
		content: data.content || '',
		image: data.image,
		type: data.type || 'info',
	};
	visible.value = true;

	// Add listener after a brief delay to prevent immediate closing if triggered by click
	setTimeout(() => {
		window.addEventListener('click', close);
	}, 100);
};

onMounted(() => {
	socket.on('global_notification', (data: any) => {
		show(data);
	});
});

onUnmounted(() => {
	socket.off('global_notification');
	window.removeEventListener('click', close);
});
</script>
