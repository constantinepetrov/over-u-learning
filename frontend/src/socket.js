import { io } from 'socket.io-client'
import { socketio_port } from '../../../../sites/common_site_config.json'

export function initSocket() {
	let host = window.location.origin
	let siteName = window.site_name || window.location.hostname

	if (window.dev_server) {
		const protocol = window.location.protocol
		const port = socketio_port || 9000
		host = `${protocol}//${window.location.hostname}:${port}`
	}

	let url = `${host}/${siteName}`

	let socket = io(url, {
		withCredentials: true,
		reconnectionAttempts: 5,
	})
	return socket
}
