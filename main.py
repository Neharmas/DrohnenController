import math
import sys
import struct

import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap, QCursor
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QMainWindow, QVBoxLayout, QHBoxLayout, QGraphicsView
import MapWidget

import socket
import threading
import pygame

def clamp(number, minimum, maximum):
    return max(minimum, min(number, maximum))

def normalize_input(left, right):
    return left * -1 + right

class SocketBridge(QObject):
    client_connected = pyqtSignal(object)  # Signal mit dem Socket-Objekt
    client_disconnected = pyqtSignal(object)
    frame_received = pyqtSignal(bytes)

class ControllerEvent:
    def __init__(self, window):
        super().__init__()
        self.window = window

        pygame.init()

        self.joysticks = []
        self.done = False

        self.deadzone = 0.3
        self.controller_input_map = {
            "buttons": {
                0:  ("move_z", -1),  # move_z_down
                1:  ("move_z", +1),  # move_z_up
                3:  ("is_infrared", "toggle"),
                9:  ("rotate", +1),  # turn_left
                10: ("rotate", -1),  # turn_right
                11: ("zoom", +1),
                12: ("zoom", -1)
            },
            "axes": {
                0: "move_y",
                1: "move_x",
                2: "look_x",
                3: "look_y",
            }
        }

        self.pressed_keys = {
            ## Drone Body
            "move_z": 0, "move_y": 0, "move_x": 0, "rotate": 0,
            ## Camera
            "look_x": 0, "look_y": 0, "zoom": 0,
            "is_infrared": False
        }
    def event_loop(self):
        event_list = pygame.event.get()
        if len(event_list) == 0:
            return
        for event in event_list:
            event_type = event.type

            # 4352 -> AudioDeviceAdded event
            # 1541 -> JoyDeviceAdded event
            if event_type in [4352]:
                return

            prev_input = self.pressed_keys.copy()

            # --- Button pressed ---
            if event.type == pygame.JOYBUTTONDOWN:
                if event.button in self.controller_input_map["buttons"]:
                    key, value = self.controller_input_map["buttons"][event.button]
                    if key == "is_infrared":
                        self.pressed_keys[key] = not self.pressed_keys[key]
                    else:
                        self.pressed_keys[key] += value
                    self.pressed_keys["zoom"] = clamp(self.pressed_keys["zoom"], 0, 2)

            # --- Button released ---
            if event.type == pygame.JOYBUTTONUP:
                if event.button in self.controller_input_map["buttons"]:
                    key, value = self.controller_input_map["buttons"][event.button]
                    if key not in ["is_infrared", "zoom"]:  # toggle bleibt wie er ist
                        self.pressed_keys[key] -= value

            # --- Controller Achsen (analog sticks, trigger) ---
            if event.type == pygame.JOYAXISMOTION:
                if event.axis in self.controller_input_map["axes"]:
                    key = self.controller_input_map["axes"][event.axis]
                    value = event.value

                    ## Invertiere X-/Y-Achsen vom Stick
                    if event.axis == 1:
                        value *= -1

                    # Deadzone anwenden
                    if abs(value) < self.deadzone:
                        value = 0

                    self.pressed_keys[key] = value

            # Handle hotplugging
            if event_type == pygame.JOYDEVICEADDED:
                # This event will be generated when the program starts for every
                # joystick, filling up the list without needing to create them manually.
                joy = pygame.joystick.Joystick(event.device_index)
                joy.init()
                self.joysticks.append(joy)
                print(f"Joystick {joy.get_instance_id()} connected")

            if event.type == pygame.JOYDEVICEREMOVED:
                del self.joysticks[event.instance_id]
                print(f"Joystick {event.instance_id} disconnected")

            if prev_input != self.pressed_keys:
                self.window.pressed_keys = self.pressed_keys

class MainWindow(QMainWindow):
    def __init__(self, bridge: SocketBridge):
        super().__init__()

        self.resize(1280, 720)
        self.setMinimumSize(800, 600)

        self.conn = None
        # connect bridge signals
        bridge.client_connected.connect(self.set_client_connection)
        bridge.client_disconnected.connect(self.clear_client_connection)
        bridge.frame_received.connect(self.on_frame)

        # Richtung der Tastendrucke (Taste → Key in pressed_keys + Richtung)
        self.KEY_MAP = {
            Qt.Key.Key_W: ("move_x", +1),
            Qt.Key.Key_S: ("move_x", -1),
            Qt.Key.Key_A: ("move_y", +1),
            Qt.Key.Key_D: ("move_y", -1),
            Qt.Key.Key_Space: ("move_z", +1),
            Qt.Key.Key_Control: ("move_z", -1),
            Qt.Key.Key_Q: ("rotate", +1),
            Qt.Key.Key_E: ("rotate", -1),
        }

        self.pressed_keys = {
            ## Drone Body
            "move_z": 0, "move_y": 0, "move_x": 0, "rotate": 0,
            ## Camera
            "look_x": 0, "look_y": 0, "zoom": 0,
            "is_infrared": False
        }

        self.is_left_mouse_clicked = False
        self.prev_is_left_mouse_clicked = False
        self.last_mouse_pos = None
        self.controller_input = ControllerEvent(self)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_loop)
        self.timer.start(16)

        # GUI
        central = QWidget(self)
        self.setCentralWidget(central)

        layout = QHBoxLayout(central)

        # Videofeed
        self.video_label = QLabel("Kein Video...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: black;")
        layout.addWidget(self.video_label, stretch=1)

        # === Minimap Overlay ===
        self.map_widget = MapWidget.MapWidgetNew()
        self.minimap = QGraphicsView(self.map_widget, self.video_label)
        self.minimap.setStyleSheet("background: rgba(40, 40, 40, 122); border: solid; border-color: grey; border-width: 1px;")
        self.minimap.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.minimap.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.minimap.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        padding = 10
        self.minimap.setGeometry(padding, padding, 200, 200)  # top-left overlay

        # === Debug Info ===
        self.debug_input_label = QLabel()
        self.debug_input_label.setStyleSheet("color: white; background-color: rgba(0,0,0,100); padding: 5px;")
        layout.addWidget(self.debug_input_label)
        self.update_input()

        self.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if hasattr(self, "minimap") and self.minimap is not None:
            # Dynamische Größe (z. B. 20% der Videobreite)
            video_width = self.video_label.width()
            video_height = self.video_label.height()

            #map_size = self.minimap.size().width()

            # Position unten links im Video
            #margin = 20
            #self.minimap.move(margin, video_height - map_size - margin)

    def closeEvent(self, a0):
        self.controller_input.done = True
        super().closeEvent(a0)

    def keyPressEvent(self, event):
        key = event.key()

        if key in self.KEY_MAP:
            axis, direction = self.KEY_MAP[key]
            # Nur erhöhen, wenn aktuell "neutral" in diese Richtung
            if self.pressed_keys[axis] == 0:
                self.pressed_keys[axis] += direction

        elif key == Qt.Key.Key_F:
            self.pressed_keys["is_infrared"] = not self.pressed_keys["is_infrared"]

    def keyReleaseEvent(self, event):
        key = event.key()

        if key in self.KEY_MAP:
            axis, direction = self.KEY_MAP[key]
            # Nur zurücksetzen, wenn es noch in dieser Richtung aktiv war
            if self.pressed_keys[axis] == direction:
                self.pressed_keys[axis] -= direction

    def mousePressEvent(self, event):
        self.is_left_mouse_clicked = True

    def mouseReleaseEvent(self, event):
        self.is_left_mouse_clicked = False

    def wheelEvent(self, event):
        wheel_rot = event.angleDelta().y()
        self.pressed_keys["zoom"] += np.sign(wheel_rot)
        self.pressed_keys["zoom"] = clamp(self.pressed_keys["zoom"], 0, 2)

    def update_loop(self):
        if self.is_left_mouse_clicked:
            pos = QCursor.pos()
            if self.last_mouse_pos is None:
                self.last_mouse_pos = pos
                return

            sensitivity = 0.05
            dx = (pos.x() - self.last_mouse_pos.x()) * sensitivity
            dy = (pos.y() - self.last_mouse_pos.y()) * sensitivity

            self.pressed_keys["look_x"] = clamp(dx, -1, 1)
            self.pressed_keys["look_y"] = clamp(dy, -1, 1) * -1
            self.last_mouse_pos = pos
        else:
            if not self.is_left_mouse_clicked and self.prev_is_left_mouse_clicked:
                self.pressed_keys["look_x"] = 0
                self.pressed_keys["look_y"] = 0

        self.prev_is_left_mouse_clicked = self.is_left_mouse_clicked
        self.update_input()

    def update_input(self):
        data = ""
        for key, value in self.pressed_keys.items():
            data += f"{key}: {value}\n"
        self.debug_input_label.setText(data)
        self.send_input_data_over_socket(data)

    def set_client_connection(self, conn):
        """Wird vom Signal aufgerufen (Hauptthread)."""
        self.conn = conn
        print("Client im GUI registriert.")

    def clear_client_connection(self):
        """Kann aufgerufen werden, wenn Verbindung beendet wird."""
        self.conn = None

        self.video_label.clear()
        self.video_label.setText("Kein Video...")
        print("Client getrennt.")

    def on_frame(self, frame_data: bytes):
        np_arr = np.frombuffer(frame_data, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        h, w, ch = img.shape
        qimg = QImage(img.data, w, h, ch * w, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)

        # keep aspect ratio with window
        self.video_label.setPixmap(
            pixmap.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

    def send_input_data_over_socket(self, data):
        if not self.conn: # ✅ Check if connected
            return
        try:
            self.conn.send(bytes(data, "utf-8"))
        except Exception as e:
            self.conn = None
            print(f"Send failed: {e}")

def loop_controller(window):
    while not window.controller_input.done:
        window.controller_input.event_loop()
    pygame.quit()

def recv_all(conn, length):
    buf = b''
    while len(buf) < length:
        data = conn.recv(length - len(buf))
        if not data:
            return None
        buf += data
    return buf

def handle_client(server_socket, bridge: SocketBridge):
    while True:
        conn, addr = server_socket.accept()
        print(f"🔗 Connected by: {addr}")

        bridge.client_connected.emit(conn)

        try:
            while True:
                len_bytes = recv_all(conn, 4)
                if not len_bytes:
                    break
                length = struct.unpack(">I", len_bytes)[0]
                frame_data = recv_all(conn, length)
                if not frame_data:
                    break
                bridge.frame_received.emit(frame_data)

        except Exception as e:
            print(f"⚠️ Client error: {e}")

        finally:
            conn.close()
            print(f"❌ Connection closed: {addr}")
            bridge.client_disconnected.emit(conn)

def create_socket():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(("0.0.0.0", 8080))
    server_socket.listen()
    print("Server Listening...")
    return server_socket

def main():
    server_socket = create_socket()

    app = QApplication(sys.argv)
    bridge = SocketBridge()
    window = MainWindow(bridge)
    window.show()

    # handle controller input in the background
    threading.Thread(target=loop_controller, args=(window,), daemon=True).start()

    # handle client in the background
    threading.Thread(
        target=handle_client,
        args=(server_socket, bridge),
        daemon=True
    ).start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()