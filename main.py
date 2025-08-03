import sys

import pygame

from PyQt6.QtGui import QKeyEvent, QImage
from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QMainWindow, QGridLayout

from layout_colorwidget import Color


def clamp(number, minimum, maximum):
    return max(minimum, min(number, maximum))

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

    def mapJoystickToKeyboard(self):
        pass
        # TODO: SEPERATE INPUT AND MAP IT TO THE MAIN WINDOW APPLICATION
        #       WRITE SOCKET OUTPUT TO RASPBERRY PI

    def eventLoop(self):
        for event in pygame.event.get():
            if event.type == pygame.JOYBUTTONDOWN:
                print("Joystick button pressed.")
                if event.button == 0:
                    joystick = self.joysticks[event.instance_id]
                    if joystick.rumble(0, 0.7, 500):
                        print(f"Rumble effect played on joystick {event.instance_id}")

            if event.type == pygame.JOYBUTTONUP:
                print("Joystick button released.")

            if event.type == pygame.JOYAXISMOTION:
                if event.axis == 0:
                    print("Left Movement: ", event.value)

            # Handle hotplugging
            if event.type == pygame.JOYDEVICEADDED:
                # This event will be generated when the program starts for every
                # joystick, filling up the list without needing to create them manually.
                joy = pygame.joystick.Joystick(event.device_index)
            #    joysticks[joy.get_instance_id()] = joy
                print(f"Joystick {joy.get_instance_id()} connected")

            if event.type == pygame.JOYDEVICEREMOVED:
                del self.joysticks[event.instance_id]
                print(f"Joystick {event.instance_id} disconnected")


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

        layout = QGridLayout()
        layout.addWidget(Color("grey"), 0, 1)
        layout.addWidget(Color("grey"), 1, 0)
        layout.addWidget(Color("grey"), 1, 1)
        layout.addWidget(Color("grey"), 1, 2)
        layout.addWidget(Color("grey"), 2, 1)

        widget = QWidget()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

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

            self.updateInput()
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

            self.updateInput()
            #self.key_label.setText(f"Key Released: {key_text}")

    def updateInput(self):
        self.move_x = self.clampMovement(self.move_x, "move_forward", "move_back")
        self.move_y = self.clampMovement(self.move_y, "move_left", "move_right")
        self.move_z = self.clampMovement(self.move_z, "move_up", "move_down")
        self.rotate = self.clampMovement(self.rotate, "turn_right", "turn_left")
        print("X: " + str(self.move_x) + "\nY: " + str(self.move_y) + "\nZ: " + str(self.move_z) + "\nrot " + str(self.rotate) + "\n")

    def clampMovement(self, number, first_input, second_input):
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