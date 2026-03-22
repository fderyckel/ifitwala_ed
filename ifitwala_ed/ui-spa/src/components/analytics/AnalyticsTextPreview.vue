<template>
	<div
		ref="triggerRef"
		class="analytics-text-preview"
		:class="{ 'analytics-text-preview--interactive': isOverflowing }"
		:tabindex="isOverflowing ? 0 : undefined"
		:role="isOverflowing ? 'button' : undefined"
		:aria-expanded="isOverflowing ? isOpen : undefined"
		aria-haspopup="dialog"
		@click="onTriggerClick"
		@mouseenter="openPreview"
		@mouseleave="scheduleClose"
		@focusin="openPreview"
		@focusout="closePreview"
		@keydown.enter.prevent="openPreview"
		@keydown.space.prevent="openPreview"
		@keydown.esc.prevent.stop="closePreview"
	>
		<span
			ref="contentRef"
			class="analytics-text-preview__content"
			:style="{ '--analytics-text-preview-lines': String(lines) }"
		>
			{{ text }}
		</span>
	</div>

	<Teleport to="body">
		<div
			v-if="isOpen && isOverflowing"
			ref="panelRef"
			class="analytics-text-preview__panel"
			:style="panelStyle"
			@mouseenter="cancelClose"
			@mouseleave="scheduleClose"
		>
			<div class="analytics-text-preview__panel-body">
				{{ text }}
			</div>
		</div>
	</Teleport>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';

const props = withDefaults(
	defineProps<{
		text: string;
		lines?: number;
		previewWidth?: number;
	}>(),
	{
		lines: 2,
		previewWidth: 560,
	}
);

const triggerRef = ref<HTMLElement | null>(null);
const contentRef = ref<HTMLElement | null>(null);
const panelRef = ref<HTMLElement | null>(null);
const isOpen = ref(false);
const isOverflowing = ref(false);
const panelStyle = ref<Record<string, string>>({});

let closeTimer: ReturnType<typeof setTimeout> | null = null;

async function syncOverflowState() {
	await nextTick();
	const content = contentRef.value;
	if (!content) {
		isOverflowing.value = false;
		return;
	}

	isOverflowing.value =
		content.scrollHeight > content.clientHeight + 1 ||
		content.scrollWidth > content.clientWidth + 1;
}

async function updatePanelPosition() {
	await nextTick();

	const trigger = triggerRef.value;
	if (!trigger) return;

	const rect = trigger.getBoundingClientRect();
	const viewportWidth = window.innerWidth;
	const panelWidth = Math.min(props.previewWidth, Math.max(280, viewportWidth - 24));
	const left = Math.min(Math.max(rect.left, 12), viewportWidth - panelWidth - 12);
	const prefersAbove = window.innerHeight - rect.bottom < 220 && rect.top > window.innerHeight / 2;

	panelStyle.value = {
		position: 'fixed',
		width: `${panelWidth}px`,
		maxWidth: 'calc(100vw - 24px)',
		left: `${left}px`,
		top: prefersAbove ? `${Math.max(rect.top - 10, 12)}px` : `${rect.bottom + 10}px`,
		transform: prefersAbove ? 'translateY(-100%)' : 'none',
		zIndex: '160',
	};
}

async function openPreview() {
	cancelClose();
	await syncOverflowState();
	if (!isOverflowing.value) return;

	isOpen.value = true;
	await updatePanelPosition();
	bindViewportListeners();
}

function closePreview() {
	cancelClose();
	isOpen.value = false;
	unbindViewportListeners();
}

function scheduleClose() {
	cancelClose();
	closeTimer = setTimeout(() => {
		closePreview();
	}, 120);
}

function cancelClose() {
	if (!closeTimer) return;
	clearTimeout(closeTimer);
	closeTimer = null;
}

async function onViewportChange() {
	if (!isOpen.value) return;
	await syncOverflowState();
	if (!isOverflowing.value) {
		closePreview();
		return;
	}
	await updatePanelPosition();
}

function onDocumentPointerDown(event: MouseEvent | TouchEvent) {
	const target = event.target as Node | null;
	if (!target) return;

	if (triggerRef.value?.contains(target) || panelRef.value?.contains(target)) {
		return;
	}

	closePreview();
}

function onDocumentKeydown(event: KeyboardEvent) {
	if (event.key === 'Escape') {
		closePreview();
	}
}

function bindViewportListeners() {
	window.addEventListener('resize', onViewportChange);
	window.addEventListener('scroll', onViewportChange, true);
	document.addEventListener('mousedown', onDocumentPointerDown);
	document.addEventListener('touchstart', onDocumentPointerDown, { passive: true });
	document.addEventListener('keydown', onDocumentKeydown);
}

function unbindViewportListeners() {
	window.removeEventListener('resize', onViewportChange);
	window.removeEventListener('scroll', onViewportChange, true);
	document.removeEventListener('mousedown', onDocumentPointerDown);
	document.removeEventListener('touchstart', onDocumentPointerDown);
	document.removeEventListener('keydown', onDocumentKeydown);
}

async function onTriggerClick(event: MouseEvent) {
	await syncOverflowState();
	if (!isOverflowing.value) return;

	event.stopPropagation();
	if (isOpen.value) {
		closePreview();
		return;
	}

	openPreview();
}

onBeforeUnmount(() => {
	cancelClose();
	unbindViewportListeners();
});

onMounted(() => {
	syncOverflowState();
});

watch(
	() => [props.text, props.lines],
	() => {
		syncOverflowState();
	}
);
</script>

<style scoped>
.analytics-text-preview {
	display: block;
	width: 100%;
}

.analytics-text-preview--interactive {
	cursor: pointer;
}

.analytics-text-preview__content {
	display: -webkit-box;
	overflow: hidden;
	text-overflow: ellipsis;
	white-space: normal;
	word-break: break-word;
	-webkit-box-orient: vertical;
	-webkit-line-clamp: var(--analytics-text-preview-lines);
}

.analytics-text-preview__panel {
	border: 1px solid rgba(148, 163, 184, 0.22);
	border-radius: 1rem;
	background:
		linear-gradient(145deg, rgba(255, 252, 247, 0.98), rgba(255, 255, 255, 0.99)),
		rgba(255, 255, 255, 0.99);
	box-shadow:
		0 18px 44px rgba(15, 23, 42, 0.18),
		0 2px 10px rgba(15, 23, 42, 0.08);
}

.analytics-text-preview__panel-body {
	max-height: min(24rem, calc(100vh - 3rem));
	overflow: auto;
	padding: 0.95rem 1.05rem;
	font-size: 0.98rem;
	line-height: 1.6rem;
	color: rgb(15 23 42);
	white-space: pre-wrap;
	word-break: break-word;
}
</style>
