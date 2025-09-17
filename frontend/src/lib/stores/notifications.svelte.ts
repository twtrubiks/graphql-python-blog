interface Notification {
	id: string;
	message: string;
	type: 'info' | 'success' | 'warning' | 'error';
	duration?: number;
	link?: { text: string; href: string };
}

class NotificationStore {
	notifications = $state<Notification[]>([]);

	add(notification: Omit<Notification, 'id'>) {
		const id = Math.random().toString(36).substring(7);
		this.notifications = [
			...this.notifications,
			{
				id,
				duration: 5000,
				...notification
			}
		];

		// 自動移除
		if (notification.duration !== 0) {
			setTimeout(() => {
				this.remove(id);
			}, notification.duration || 5000);
		}

		return id;
	}

	remove(id: string) {
		this.notifications = this.notifications.filter(n => n.id !== id);
	}

	clear() {
		this.notifications = [];
	}

	// 快捷方法
	info(message: string, options?: Partial<Notification>) {
		return this.add({ ...options, message, type: 'info' });
	}

	success(message: string, options?: Partial<Notification>) {
		return this.add({ ...options, message, type: 'success' });
	}

	warning(message: string, options?: Partial<Notification>) {
		return this.add({ ...options, message, type: 'warning' });
	}

	error(message: string, options?: Partial<Notification>) {
		return this.add({ ...options, message, type: 'error' });
	}
}

export const notifications = new NotificationStore();