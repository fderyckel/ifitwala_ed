import { SIGNAL_TASK_DELIVERY_CREATED, uiSignals } from '@/lib/uiSignals';
import type { TaskDeliveryCreatedSignal } from '@/types/tasks';

export function emitTaskDeliveryCreatedSignal(payload: TaskDeliveryCreatedSignal) {
	uiSignals.emit(SIGNAL_TASK_DELIVERY_CREATED, payload);
}
