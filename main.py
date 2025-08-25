import struct
import sys
import faulthandler

import cv2
import numpy as np
from PyQt6.QtCore import QObject, pyqtSignal, Qt, QTimer, QSocketNotifier
from PyQt6.QtGui import QKeyEvent, QImage, QPixmap, QWheelEvent, QCursor
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QMainWindow, QGridLayout, QVBoxLayout

import cv2 as cv

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
        for i in range(pygame.joystick.get_count()):
            self.joysticks.append(pygame.joystick.Joystick(i))
            self.joysticks[i].init()

        self.done = False

        self.deadzone = 0.2
        self.controller_input_map = {
            "buttons" : {
                0: "move_z_down", 1: "move_z_up",
                4: "turn_left", 5: "turn_right"
            },
            "axes" : {
                0: "move_y", 1: "move_x",
                3: "look_x", 4: "look_y",
                2: "zoom_out", 5: "zoom_in",
            }
        }

        self.pressed_keys = {
                            "move_z_down" : 0, "move_z_up" : 0,
                             "turn_left" : 0, "turn_right": 0,
                             "move_y" : 0, "move_x" : 0,
                             "look_x" : 0, "look_y" : 0,
                             "zoom_in": 0, "zoom_out" : 0
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
            if event_type == pygame.JOYBUTTONDOWN:
                map = self.controller_input_map["buttons"]
                if event.button in map:
                    self.pressed_keys[map[event.button]] = 1

            if event_type == pygame.JOYBUTTONUP:
                map = self.controller_input_map["buttons"]
                if event.button in map:
                    self.pressed_keys[map[event.button]] = 0

            if event_type == pygame.JOYAXISMOTION:
                map = self.controller_input_map["axes"]
                value = event.value

                # Inverted for some reason
                if event.axis in [0, 1]:
                    value*=-1

                #if self.pressed_keys[map[event.axis]] == value:
                #    return

                if abs(value) < self.deadzone:
                    self.pressed_keys[map[event.axis]] = 0
                else:
                    self.pressed_keys[map[event.axis]] = value

            # Handle hotplugging
            if event_type == pygame.JOYDEVICEADDED:
                # This event will be generated when the program starts for every
                # joystick, filling up the list without needing to create them manually.
                joy = pygame.joystick.Joystick(event.device_index)
                self.joysticks[joy.get_instance_id() - 1] = joy
                print(f"Joystick {joy.get_instance_id()} connected")

            if event.type == pygame.JOYDEVICEREMOVED:
                del self.joysticks[event.instance_id]
                print(f"Joystick {event.instance_id} disconnected")

            if prev_input != self.pressed_keys:
                move_z = normalize_input(self.pressed_keys["move_z_down"], self.pressed_keys["move_z_up"])
                rotate = normalize_input(self.pressed_keys["turn_left"], self.pressed_keys["turn_right"])
                #self.window.update_input(self.pressed_keys["move_x"], self.pressed_keys["move_y"], move_z, rotate, True)
                print("update")

class MainWindow(QMainWindow):
    def __init__(self, bridge: SocketBridge):
        super().__init__()

        self.conn = None

        self.controllerInput = ControllerEvent(self)

        self.isLeftMouseClicked = False
        self.last_mouse_pos = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_loop)
        self.timer.start(16)

        layout = QVBoxLayout()

        # video label
        self.video_label = QLabel("Waiting for video...")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Beispiel-UI
        self.connection_status = QLabel("Kein Client verbunden")
        self.connection_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.connection_status)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.addWidget(self.video_label, stretch=1)
        layout.addWidget(self.connection_status)
        self.setCentralWidget(central)

        # connect bridge signals
        bridge.client_connected.connect(self.set_client_connection)
        bridge.client_disconnected.connect(self.clear_client_connection)
        bridge.frame_received.connect(self.on_frame)

        self.pressed_keys = {
            ## Drone Body
            "move_z": 0, "move_y": 0, "move_x": 0, "rotate" : 0,
            ## Camera
            "look_x": 0, "look_y": 0, "zoom": 0,
            "is_infrared": False
        }

        self.label = QLabel()
        self.update_input()
        layout.addWidget(self.label)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        widget.show()

    def closeEvent(self, a0):
        self.controllerInput.done = True
        super().closeEvent(a0)

    def keyPressEvent(self, event):
        key_text = event.text().strip()
        match key_text:
            case "w":
                self.pressed_keys["move_x"] += 1
            case "s":
                self.pressed_keys["move_x"] -= 1
            case "d":
                self.pressed_keys["move_y"] -= 1
            case "a":
                self.pressed_keys["move_y"] += 1
            case "":
                # Keyboard = Space
                if event.key() == 32:
                    self.pressed_keys["move_z"] = 1
                # Keyboard = Control/Steuerung
                elif event.key() == 16777249:
                    self.pressed_keys["move_z"] = -1
            case "q":
                self.pressed_keys["rotate"] = 1
            case "e":
                self.pressed_keys["rotate"] = -1
            case "f":
                self.pressed_keys["is_infrared"] = not self.pressed_keys["is_infrared"]

    def keyReleaseEvent(self, event):
        key_text = event.text().strip()
        match key_text:
            case "w" | "s":
                self.pressed_keys["move_x"] = 0
            case "d" | "a":
                self.pressed_keys["move_y"] = 0
            case "":
                # Keyboard = Space und Control/Steuerung
                if event.key() in [32, 16777249]:
                    self.pressed_keys["move_z"] = 0
            case "q" | "e":
                self.pressed_keys["rotate"] = 0

    def mousePressEvent(self, event):
        self.isLeftMouseClicked = True

    def mouseReleaseEvent(self, event):
        self.isLeftMouseClicked = False

    def wheelEvent(self, event):
        wheel_rot = event.angleDelta().y()
        self.pressed_keys["zoom"] += clamp(wheel_rot, -1, 1)

    def update_loop(self):
        if self.isLeftMouseClicked:
            pos = QCursor.pos()
            if self.last_mouse_pos is None:
                self.last_mouse_pos = pos
                return
            dx = pos.x() - self.last_mouse_pos.x()
            dy = pos.y() - self.last_mouse_pos.y()
            self.pressed_keys["look_x"] = dx
            self.pressed_keys["look_y"] = -1 * dy
            self.last_mouse_pos = pos
        else:
            self.pressed_keys["look_x"] = 0
            self.pressed_keys["look_y"] = 0

        self.update_input()

    def update_input(self):
        for key, value in self.pressed_keys.items():
            if key == "is_infrared":
                continue
            self.pressed_keys[key] = clamp(value, -1, 1)

        data = ""
        for key, value in self.pressed_keys.items():
            data += f"{key}: {value}\n"
        self.label.setText(data)
        self.send_input_data_over_socket(self.pressed_keys)

    def set_client_connection(self, conn):
        """Wird vom Signal aufgerufen (Hauptthread)."""
        self.conn = conn
        self.connection_status.setText("Client verbunden")
        print("Client im GUI registriert.")

    def clear_client_connection(self):
        """Kann aufgerufen werden, wenn Verbindung beendet wird."""
        self.conn = None
        self.connection_status.setText("Kein Client verbunden")

        self.video_label.clear()
        self.video_label.setText("Waiting for video...")
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
        if self.conn:  # ✅ Check if connected
            try:
                self.conn.send(bytes(data, "utf-8"))
            except Exception as e:
                self.conn = None
                print(f"Send failed: {e}")

def loop_controller(window):
    while not window.controllerInput.done:
        window.controllerInput.event_loop()
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

        conn.setblocking(False)

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

    #bridge = SocketBridge()
    #bridge.client_connected.connect(window.set_client_connection)
    #bridge.client_disconnected.connect(window.clear_client_connection)

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