import pyautogui


class PointerController:

    def __init__(self, frame_width, frame_height):

        # ==========================================================
        # CAMERA FRAME
        # ==========================================================

        self.frame_width = frame_width
        self.frame_height = frame_height

        # ==========================================================
        # WINDOWS SCREEN
        # ==========================================================

        self.screen_width, self.screen_height = pyautogui.size()

        # ==========================================================
        # POINTER SMOOTHING
        # ==========================================================

        self.smoothing = 0.30

        self.previous_x = None
        self.previous_y = None

        # ==========================================================
        # POINTER LOCK
        # ==========================================================

        self.locked = False

        self.locked_x = None
        self.locked_y = None

        # ==========================================================
        # SCROLL
        # ==========================================================

        self.last_scroll_y = None
        self.scroll_accumulator = 0.0

        self.scroll_divisor = 2.0
        self.scroll_deadzone = 2.0
        self.max_scroll_per_frame = 18
        self.scroll_gain = 1.8

        # ==========================================================
        # DRAG
        # ==========================================================

        self.dragging = False

        self.drag_start_x = None
        self.drag_start_y = None

        self.drag_threshold = 12

        # ==========================================================
        # PYAUTOGUI
        # ==========================================================

        pyautogui.PAUSE = 0.01

    # ==============================================================
    # CAMERA -> SCREEN
    # ==============================================================

    def camera_to_screen(self, finger_x, finger_y):

        target_x = int(
            (
                (self.frame_width - finger_x)
                / self.frame_width
            )
            * self.screen_width
        )

        target_y = int(
            (
                finger_y
                / self.frame_height
            )
            * self.screen_height
        )

        target_x = max(
            0,
            min(
                self.screen_width - 1,
                target_x
            )
        )

        target_y = max(
            0,
            min(
                self.screen_height - 1,
                target_y
            )
        )

        return target_x, target_y

    # ==============================================================
    # MOVE POINTER
    # ==============================================================

    def move(self, finger_x, finger_y):

        if self.locked:
            return

        if self.dragging:
            return

        target_x, target_y = self.camera_to_screen(
            finger_x,
            finger_y
        )

        # ----------------------------------------------------------
        # FIRST POSITION
        # ----------------------------------------------------------

        if self.previous_x is None:

            self.previous_x = target_x
            self.previous_y = target_y

            pyautogui.moveTo(
                target_x,
                target_y,
                duration=0
            )

            return

        # ----------------------------------------------------------
        # SMOOTHING
        # ----------------------------------------------------------

        smooth_x = (
            self.previous_x
            +
            (
                target_x
                - self.previous_x
            )
            * self.smoothing
        )

        smooth_y = (
            self.previous_y
            +
            (
                target_y
                - self.previous_y
            )
            * self.smoothing
        )

        # ----------------------------------------------------------
        # MOVE
        # ----------------------------------------------------------

        pyautogui.moveTo(
            int(smooth_x),
            int(smooth_y),
            duration=0
        )

        self.previous_x = smooth_x
        self.previous_y = smooth_y

    # ==============================================================
    # LOCK
    # ==============================================================

    def lock(self):

        if self.locked:
            return

        if self.previous_x is None:

            current_x, current_y = pyautogui.position()

            self.previous_x = current_x
            self.previous_y = current_y

        self.locked_x = int(self.previous_x)
        self.locked_y = int(self.previous_y)

        self.locked = True

        pyautogui.moveTo(
            self.locked_x,
            self.locked_y,
            duration=0
        )

        print(
            f"[POINTER] LOCKED at "
            f"({self.locked_x}, {self.locked_y})"
        )

    # ==============================================================
    # UNLOCK
    # ==============================================================

    def unlock(self):

        if not self.locked:
            return

        self.locked = False

        print("[POINTER] UNLOCKED")

    # ==============================================================
    # LOCK STATUS
    # ==============================================================

    def is_locked(self):

        return self.locked

    # ==============================================================
    # CLICK
    # ==============================================================

    def click(self):

        print("[ACTION] LEFT CLICK")

        pyautogui.click()

    # ==============================================================
    # DOUBLE CLICK
    # ==============================================================

    def double_click(self):

        print("[ACTION] DOUBLE CLICK / OPEN")

        pyautogui.doubleClick(
            interval=0.10
        )

    # ==============================================================
    # RIGHT CLICK
    # ==============================================================

    def right_click(self):

        print("[ACTION] RIGHT CLICK")

        pyautogui.click(
            button="right"
        )

    # ==============================================================
    # START DRAG
    # ==============================================================

    def start_drag(self):

        if self.dragging:
            return

        current_x, current_y = pyautogui.position()

        self.drag_start_x = current_x
        self.drag_start_y = current_y

        pyautogui.mouseDown(
            button="left"
        )

        self.dragging = True

        print("[ACTION] DRAG STARTED")

    # ==============================================================
    # UPDATE DRAG
    # ==============================================================

    def update_drag(
        self,
        finger_x,
        finger_y
    ):

        if not self.dragging:
            return

        target_x, target_y = self.camera_to_screen(
            finger_x,
            finger_y
        )

        # Direct movement during drag is intentional.
        pyautogui.moveTo(
            target_x,
            target_y,
            duration=0
        )

        self.previous_x = target_x
        self.previous_y = target_y

    # ==============================================================
    # END DRAG
    # ==============================================================

    def end_drag(self):

        if not self.dragging:
            return

        pyautogui.mouseUp(
            button="left"
        )

        self.dragging = False

        print(
            "[ACTION] DRAG RELEASED / DROP"
        )

        self.drag_start_x = None
        self.drag_start_y = None

    # ==============================================================
    # DRAG STATUS
    # ==============================================================

    def is_dragging(self):

        return self.dragging

    # ==============================================================
    # SCROLL
    # ==============================================================

    def scroll(self, current_y):

        # Never scroll while dragging.
        if self.dragging:
            return 0

        if self.last_scroll_y is None:

            self.last_scroll_y = current_y
            self.scroll_accumulator = 0.0

            return 0

        # ----------------------------------------------------------
        # VERTICAL MOVEMENT
        # ----------------------------------------------------------

        delta_y = (
            self.last_scroll_y
            - current_y
        )

        self.last_scroll_y = current_y

        # ----------------------------------------------------------
        # DEADZONE
        # ----------------------------------------------------------

        if abs(delta_y) < self.scroll_deadzone:
            return 0

        # ----------------------------------------------------------
        # GAIN
        # ----------------------------------------------------------

        wheel_delta = (
            delta_y
            / self.scroll_divisor
            * self.scroll_gain
        )

        self.scroll_accumulator += wheel_delta

        # ----------------------------------------------------------
        # INTEGER WHEEL UNITS
        # ----------------------------------------------------------

        scroll_amount = int(
            self.scroll_accumulator
        )

        if scroll_amount == 0:
            return 0

        # ----------------------------------------------------------
        # LIMIT
        # ----------------------------------------------------------

        scroll_amount = max(
            -self.max_scroll_per_frame,
            min(
                self.max_scroll_per_frame,
                scroll_amount
            )
        )

        # ----------------------------------------------------------
        # REMOVE USED MOVEMENT
        # ----------------------------------------------------------

        self.scroll_accumulator -= scroll_amount

        # ----------------------------------------------------------
        # WINDOWS MOUSE WHEEL
        # ----------------------------------------------------------

        pyautogui.scroll(
            scroll_amount
        )

        # ----------------------------------------------------------
        # CONSOLE
        # ----------------------------------------------------------

        if scroll_amount > 0:

            print(
                f"[ACTION] SCROLL UP "
                f"({scroll_amount})"
            )

        else:

            print(
                f"[ACTION] SCROLL DOWN "
                f"({abs(scroll_amount)})"
            )

        return scroll_amount

    # ==============================================================
    # RESET SCROLL
    # ==============================================================

    def reset_scroll(self):

        self.last_scroll_y = None
        self.scroll_accumulator = 0.0

    # ==============================================================
    # RESET EVERYTHING
    # ==============================================================

    def reset(self):

        # ----------------------------------------------------------
        # SAFELY RELEASE MOUSE
        # ----------------------------------------------------------

        if self.dragging:

            try:

                pyautogui.mouseUp(
                    button="left"
                )

            except Exception:
                pass

        # ----------------------------------------------------------
        # POINTER
        # ----------------------------------------------------------

        self.previous_x = None
        self.previous_y = None

        # ----------------------------------------------------------
        # LOCK
        # ----------------------------------------------------------

        self.locked = False

        self.locked_x = None
        self.locked_y = None

        # ----------------------------------------------------------
        # SCROLL
        # ----------------------------------------------------------

        self.last_scroll_y = None
        self.scroll_accumulator = 0.0

        # ----------------------------------------------------------
        # DRAG
        # ----------------------------------------------------------

        self.dragging = False

        self.drag_start_x = None
        self.drag_start_y = None