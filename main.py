import sys
from token import VBAREQUAL

import pygame

from PyQt6.QtGui import QKeyEvent, QImage
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QMainWindow, QGridLayout, QVBoxLayout

from layout_colorwidget import Color


def clamp(number, minimum, maximum):
    return max(minimum, min(number, maximum))

def normalizeInput(left, right):
    return left * -1 + right

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

    def mapJoystickToKeyboard(self):
        pass
        # TODO: SEPERATE INPUT AND MAP IT TO THE MAIN WINDOW APPLICATION
        #       WRITE SOCKET OUTPUT TO RASPBERRY PI

    def eventLoop(self):
        event_list = pygame.event.get()
        if len(event_list) == 0:
            return
        for event in event_list:
            event_type = event.type
            if event_type in [4352, 1541]:
                return
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

                self.pressed_keys[map[event.axis]] = value
                print(self.pressed_keys["turn_left"])

            # Handle hotplugging
            if event_type == pygame.JOYDEVICEADDED:
                # This event will be generated when the program starts for every
                # joystick, filling up the list without needing to create them manually.
                joy = pygame.joystick.Joystick(event.device_index)
                self.joysticks[joy.get_instance_id()] = joy
                print(f"Joystick {joy.get_instance_id()} connected")

            if event.type == pygame.JOYDEVICEREMOVED:
                del self.joysticks[event.instance_id]
                print(f"Joystick {event.instance_id} disconnected")

            move_z = normalizeInput(self.pressed_keys["move_z_down"], self.pressed_keys["move_z_up"])
            rotate = normalizeInput(self.pressed_keys["turn_left"], self.pressed_keys["turn_right"])
            self.window.updateInput(self.pressed_keys["move_x"], self.pressed_keys["move_y"], move_z, rotate, True)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.controllerInput = ControllerEvent(self)

        self.pressed_keys = {"move_forward", "move_left", "move_right", "move_back", "move_up", "move_down", "turn_right", "turn_left"}
        self.pressed_keys.clear()
        self.move_x = 0
        self.move_y = 0
        self.move_z = 0
        self.rotate = 0

        layout = QVBoxLayout()
        self.label = QLabel("X: " + str(self.move_x) + "\nY: " + str(self.move_y) + "\nZ: " + str(self.move_z) + "\nROT: " + str(self.rotate) + "\n")
        layout.addWidget(self.label)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)
        widget.show()

    def closeEvent(self, a0):
        self.controllerInput.done = True
        super().closeEvent(a0)

    def keyPressEvent(self, event):
        if isinstance(event, QKeyEvent):
            key_text = event.text().strip()
            match key_text:
                case "w":
                    self.pressed_keys.add("move_forward")
                case "s":
                    self.pressed_keys.add("move_back")
                case "d":
                    self.pressed_keys.add("move_right")
                case "a":
                    self.pressed_keys.add("move_left")
                case "":
                    # Keyboard = Space
                    if event.key() == 32:
                        self.pressed_keys.add("move_up")
                    # Keyboard = Control/Steuerung
                    elif event.key() == 16777249:
                        self.pressed_keys.add("move_down")
                case "q":
                    self.pressed_keys.add("turn_left")
                case "e":
                    self.pressed_keys.add("turn_right")

            self.updateInput(self.move_x, self.move_y, self.move_z, self.rotate)
            #self.key_label.setText(f"Last Key Pressed: {key_text}")

    def keyReleaseEvent(self, event):
        if isinstance(event, QKeyEvent):
            key_text = event.text().strip()
            print(key_text)
            match key_text:
                case "w":
                    self.pressed_keys.remove("move_forward")
                case "s":
                    self.pressed_keys.remove("move_back")
                case "d":
                    self.pressed_keys.remove("move_right")
                case "a":
                    self.pressed_keys.remove("move_left")
                case "":
                    # Keyboard = Space
                    if event.key() == 32:
                        self.pressed_keys.remove("move_up")
                    # Keyboard = Control/Steuerung
                    elif event.key() == 16777249:
                        self.pressed_keys.remove("move_down")
                case "q":
                    self.pressed_keys.remove("turn_left")
                case "e":
                    self.pressed_keys.remove("turn_right")

            self.updateInput(self.move_x, self.move_y, self.move_z, self.rotate)
            #self.key_label.setText(f"Key Released: {key_text}")

    def updateInput(self, move_x, move_y, move_z, rotate, controller=False):
        self.move_x = self.clampMovement(move_x, "move_forward", "move_back", controller)
        self.move_y = self.clampMovement(move_y, "move_left", "move_right", controller)
        self.move_z = self.clampMovement(move_z, "move_up", "move_down", controller)
        self.rotate = self.clampMovement(rotate, "turn_right", "turn_left", controller)

        self.label.setText("X: " + str(self.move_x) + "\nY: " + str(self.move_y) + "\nZ: " + str(self.move_z) + "\nROT: " + str(self.rotate) + "\n")
        #print("X: " + str(self.move_x) + "\nY: " + str(self.move_y) + "\nZ: " + str(self.move_z) + "\nrot " + str(self.rotate) + "\n")

    def clampMovement(self, number, first_input, second_input, controller):
        if controller:
            return clamp(number, -1, 1)
        if first_input in self.pressed_keys:
            number += 1
        if second_input in self.pressed_keys:
            number -= 1
        if first_input not in self.pressed_keys and second_input not in self.pressed_keys:
            number = 0
        return clamp(number, -1, 1)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    while not window.controllerInput.done:
        window.controllerInput.eventLoop()

    pygame.quit()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()