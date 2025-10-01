import sys
import socket, cv2, struct


def main(HOST, PORT=8080):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if ":" in HOST:
            IP, PORT = str(HOST.split(":")[0]), int(HOST.split(":")[1])
            print(f"Connecting to {HOST}...")
            s.connect((IP, PORT))
        else:
            print(f"Connecting to {HOST}:{PORT}...")
            s.connect((HOST, PORT))

        s.setblocking(False)
        print("Connection established!")
        running = True
        try:
            while running:
                ret, frame = cap.read()
                if not ret:
                    print("Skipped frame")
                    running = False
                    continue

                ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if not ret:
                    print("Encoding failed")
                    continue
                frame_data = buffer.tobytes()
                try:
                    s.sendall(struct.pack(">I", len(frame_data)) + frame_data)
                except BlockingIOError:
                    pass

                # --- Check for incoming controller messages ---
                try:
                    msg = s.recv(1024)  # adjust buffer size as needed
                    if msg:
                        # Process controller input
                        print(msg.decode())
                    else:
                        # Server closed connection
                        continue
                except BlockingIOError:
                    pass
        except KeyboardInterrupt:
            print("Interrupted by user")
        finally:
            cap.release()
            s.close()
            print("Lost connection to host")
            return


if __name__ == "__main__":
    cap = cv2.VideoCapture(0, cv2.CAP_ANY)
    if not cap.isOpened():
        sys.exit("Kamera konnte nicht initialisiert werden.")

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)

    if len(sys.argv) == 3:
        main(sys.argv[1], int(sys.argv[2]))
    elif len(sys.argv) == 2:
        main(sys.argv[1])
    else:

        print("Gib die IP-Adresse des Controllers ein: ")
        HOST = input()
        main(HOST)

