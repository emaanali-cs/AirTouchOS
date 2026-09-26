import cv2
import time
import math

from mediapipe import Image, ImageFormat
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from pointer_controller import PointerController


# ==============================================================
# AirTouchOS
# TOUCHLESS OS CONTROLLER
# ==============================================================

MODEL_PATH = "models/hand_landmarker.task"
CAMERA_ID = 0


# ==============================================================
# MEDIAPIPE
# ==============================================================

NUM_HANDS = 2

MIN_DETECTION_CONFIDENCE = 0.7
MIN_PRESENCE_CONFIDENCE = 0.7
MIN_TRACKING_CONFIDENCE = 0.7


# ==============================================================
# NORMAL PINCH
#
# THUMB + INDEX
# = LEFT CLICK
# = DRAG WHEN MOVED
# ==============================================================

PINCH_START_DISTANCE = 32
PINCH_RELEASE_DISTANCE = 52

PINCH_CONFIRM_FRAMES = 3

PINCH_COOLDOWN = 0.25


# ==============================================================
# THREE-FINGER PINCH
#
# THUMB + INDEX + MIDDLE
# = DOUBLE CLICK / OPEN
#
# IMPORTANT:
# This gesture NEVER starts a drag.
# ==============================================================

THREE_FINGER_PINCH_START_DISTANCE = 42
THREE_FINGER_PINCH_RELEASE_DISTANCE = 58


# ==============================================================
# RIGHT CLICK
#
# THUMB + RING
# = RIGHT CLICK
# ==============================================================

RIGHT_CLICK_START_DISTANCE = 45
RIGHT_CLICK_RELEASE_DISTANCE = 60

RIGHT_CLICK_CONFIRM_FRAMES = 3


# ==============================================================
# DRAG
# ==============================================================

DRAG_MOVEMENT_THRESHOLD = 12


# ==============================================================
# SCROLL
# ==============================================================

SCROLL_FINGER_DISTANCE = 90


# ==============================================================
# POINTER HOLD
# ==============================================================

POINTER_HOLD_TIME = 1.5
POINTER_HOLD_MOVEMENT_THRESHOLD = 12


# ==============================================================
# MEDIAPIPE LANDMARKER
# ==============================================================

base_options = python.BaseOptions(
    model_asset_path=MODEL_PATH
)

options = vision.HandLandmarkerOptions(
    base_options=base_options,
    running_mode=vision.RunningMode.VIDEO,
    num_hands=NUM_HANDS,
    min_hand_detection_confidence=MIN_DETECTION_CONFIDENCE,
    min_hand_presence_confidence=MIN_PRESENCE_CONFIDENCE,
    min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
)

landmarker = vision.HandLandmarker.create_from_options(
    options
)


# ==============================================================
# CAMERA
# ==============================================================

cap = cv2.VideoCapture(CAMERA_ID)

if not cap.isOpened():

    print("ERROR: Could not open camera.")

    landmarker.close()

    raise SystemExit


cap.set(
    cv2.CAP_PROP_FRAME_WIDTH,
    1280
)

cap.set(
    cv2.CAP_PROP_FRAME_HEIGHT,
    720
)


width = int(
    cap.get(
        cv2.CAP_PROP_FRAME_WIDTH
    )
)

height = int(
    cap.get(
        cv2.CAP_PROP_FRAME_HEIGHT
    )
)


# ==============================================================
# POINTER
# ==============================================================

pointer = PointerController(
    width,
    height
)


# ==============================================================
# CONSOLE
# ==============================================================

print("=" * 70)

print("                         AirTouchOS")
print("                  TOUCHLESS OS CONTROLLER")

print("=" * 70)

print("SYSTEM")
print("---------------------------------------------")
print("Camera              : ACTIVE")
print("Hand Tracking       : ACTIVE")
print("Two Hands           : ACTIVE")
print("Pointer             : ACTIVE")
print("System-wide Mouse   : ACTIVE")
print("Click               : ACTIVE")
print("Double Click        : ACTIVE")
print("Right Click         : ACTIVE")
print("Drag & Drop         : ACTIVE")
print("Mouse-Wheel Scroll  : ACTIVE")
print("Pointer Hold Lock   : ACTIVE")

print()

print("GESTURES")
print("---------------------------------------------")
print("INDEX ONLY          = MOVE POINTER")
print("THUMB + INDEX       = LEFT CLICK")
print("THUMB + INDEX + MID = DOUBLE CLICK / OPEN")
print("THUMB + RING        = RIGHT CLICK")
print("PINCH + MOVE        = DRAG")
print("RELEASE PINCH       = DROP")
print("INDEX + MIDDLE      = SCROLL")
print("OTHER GESTURES      = NO ACTION")

print()

print("POINTER LOCK")
print("---------------------------------------------")
print("Index stationary for 1.5 seconds")
print("                    -> CURSOR LOCKS")
print("Thumb + Index       -> SINGLE CLICK")
print("After click         -> CURSOR UNLOCKS")

print()

print("DRAG")
print("---------------------------------------------")
print("Thumb + Index pinch")
print("Move while pinching -> DRAG")
print("Release pinch       -> DROP")

print()

print("DOUBLE CLICK")
print("---------------------------------------------")
print("Thumb + Index + Middle")
print("                    -> DOUBLE CLICK / OPEN")
print("Movement            -> NEVER DRAGS")

print()

print("RIGHT CLICK")
print("---------------------------------------------")
print("Thumb + Ring Finger")
print("                    -> RIGHT CLICK")
print("Release and repeat  -> NEXT RIGHT CLICK")

print()

print("IMPORTANT")
print("---------------------------------------------")
print("Display             = MIRRORED")
print("MediaPipe input     = ORIGINAL")
print("Pointer X           = MIRRORED")
print("Unknown gestures    = NO ACTION")
print("Mouse actions work system-wide")

print()

print("Press Q to quit.")

print("=" * 70)


# ==============================================================
# TIMESTAMP
# ==============================================================

timestamp_ms = 0


# ==============================================================
# HAND CONNECTIONS
# ==============================================================

HAND_CONNECTIONS = [

    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),

    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),

    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),

    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),

    (13, 17),
    (17, 18),
    (18, 19),
    (19, 20),

    (0, 17),
]


# ==============================================================
# PINCH STATE
# ==============================================================

pinch_active = False
pinch_candidate_frames = 0

pinch_start_x = None
pinch_start_y = None

pinch_was_locked = False
pinch_drag_started = False

# --------------------------------------------------------------
# This stores the EXACT gesture that created the pinch.
#
# "NORMAL"       = thumb + index
# "THREE_FINGER" = thumb + index + middle
#
# Once confirmed, it NEVER changes until release.
# --------------------------------------------------------------

pinch_gesture_type = None


# ==============================================================
# RIGHT CLICK STATE
# ==============================================================

right_click_active = False
right_click_candidate_frames = 0


# ==============================================================
# HOLD STATE
# ==============================================================

hold_start_time = None

hold_reference_x = None
hold_reference_y = None


# ==============================================================
# DISPLAY STATE
#
# These variables are ONLY used for drawing UI AFTER the
# display frame is mirrored.
#
# They do NOT affect gesture recognition.
# ==============================================================

display_gesture = "NONE"

display_index_x = 0
display_index_y = 0

display_hand_active = False


# ==============================================================
# HELPER
# ==============================================================

def landmark_distance(
    a,
    b,
    frame_width,
    frame_height,
):

    ax = a.x * frame_width
    ay = a.y * frame_height

    bx = b.x * frame_width
    by = b.y * frame_height

    return math.sqrt(
        (ax - bx) ** 2
        + (ay - by) ** 2
    )


# ==============================================================
# FINGER EXTENSION
# ==============================================================

def finger_is_extended(
    landmarks,
    tip_index,
    pip_index,
    frame_width,
    frame_height,
):

    tip = landmarks[tip_index]
    pip = landmarks[pip_index]

    tip_y = tip.y * frame_height
    pip_y = pip.y * frame_height

    return tip_y < pip_y


# ==============================================================
# RESET HOLD
# ==============================================================

def reset_hold_timer():

    global hold_start_time
    global hold_reference_x
    global hold_reference_y

    hold_start_time = None
    hold_reference_x = None
    hold_reference_y = None


# ==============================================================
# RESET PINCH STATE
# ==============================================================

def reset_pinch_state():

    global pinch_active
    global pinch_candidate_frames

    global pinch_start_x
    global pinch_start_y

    global pinch_was_locked
    global pinch_drag_started

    global pinch_gesture_type

    pinch_active = False

    pinch_candidate_frames = 0

    pinch_start_x = None
    pinch_start_y = None

    pinch_was_locked = False
    pinch_drag_started = False

    pinch_gesture_type = None


# ==============================================================
# RESET RIGHT CLICK STATE
# ==============================================================

def reset_right_click_state():

    global right_click_active
    global right_click_candidate_frames

    right_click_active = False
    right_click_candidate_frames = 0


# ==============================================================
# COMPLETE PINCH RELEASE
# ==============================================================

def complete_pinch_release():

    global pinch_gesture_type

    # ----------------------------------------------------------
    # DRAG RELEASE
    #
    # ONLY NORMAL THUMB + INDEX PINCH
    # CAN EVER ENTER THIS SECTION.
    # ----------------------------------------------------------

    if pinch_drag_started:

        if pointer.is_dragging():

            pointer.end_drag()

        print(
            "[GESTURE] PINCH RELEASED -> DROP"
        )

        reset_pinch_state()

        return


    # ----------------------------------------------------------
    # LOCKED POINTER
    #
    # Locked pinch is always a SINGLE CLICK.
    # ----------------------------------------------------------

    if pinch_was_locked:

        reset_pinch_state()

        return


    # ----------------------------------------------------------
    # THREE-FINGER PINCH
    #
    # THUMB + INDEX + MIDDLE
    # = DOUBLE CLICK
    # ----------------------------------------------------------

    if pinch_gesture_type == "THREE_FINGER":

        pointer.double_click()

        print(
            "[GESTURE] "
            "THUMB + INDEX + MIDDLE "
            "-> DOUBLE CLICK / OPEN"
        )

        reset_pinch_state()

        return


    # ----------------------------------------------------------
    # NORMAL PINCH
    #
    # THUMB + INDEX
    # = SINGLE LEFT CLICK
    # ----------------------------------------------------------

    if pinch_gesture_type == "NORMAL":

        pointer.click()

        print(
            "[GESTURE] "
            "THUMB + INDEX -> LEFT CLICK"
        )

        reset_pinch_state()

        return


    # ----------------------------------------------------------
    # SAFETY RESET
    # ----------------------------------------------------------

    reset_pinch_state()


# ==============================================================
# MAIN LOOP
# ==============================================================

try:

    while True:

        # ======================================================
        # CAMERA
        # ======================================================

        success, frame = cap.read()

        if not success:

            print(
                "ERROR: Could not read camera frame."
            )

            break


        height, width, _ = frame.shape


        # ======================================================
        # RESET DISPLAY-ONLY STATE
        # ==============================================================

        display_gesture = "NONE"
        display_hand_active = False

        display_index_x = 0
        display_index_y = 0


        # ======================================================
        # MEDIAPIPE INPUT
        # ======================================================

        rgb_frame = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        mp_image = Image(
            image_format=ImageFormat.SRGB,
            data=rgb_frame
        )

        timestamp_ms += 33


        # ======================================================
        # DETECT
        # ======================================================

        result = landmarker.detect_for_video(
            mp_image,
            timestamp_ms
        )


        # ======================================================
        # DISPLAY
        # ==============================================================

        display_frame = frame.copy()

        detected_hands = []


        # ======================================================
        # HANDS FOUND
        # ======================================================

        if result.hand_landmarks:

            # --------------------------------------------------
            # PREFER RIGHT HAND
            # --------------------------------------------------

            selected_index = 0

            for i, hand_info in enumerate(
                result.handedness
            ):

                label = (
                    hand_info[0].category_name
                )

                if label == "Right":

                    selected_index = i

                    break


            # ==================================================
            # PROCESS HANDS
            # ==================================================

            for hand_index, landmarks in enumerate(
                result.hand_landmarks
            ):

                handedness = (
                    result.handedness[
                        hand_index
                    ][0]
                )

                hand_label = (
                    handedness.category_name
                )

                confidence = (
                    handedness.score
                )


                # ==================================================
                # LANDMARKS
                # ==================================================

                index_tip = landmarks[8]
                thumb_tip = landmarks[4]
                middle_tip = landmarks[12]
                ring_tip = landmarks[16]

                index_x = int(
                    index_tip.x * width
                )

                index_y = int(
                    index_tip.y * height
                )

                thumb_x = int(
                    thumb_tip.x * width
                )

                thumb_y = int(
                    thumb_tip.y * height
                )

                middle_x = int(
                    middle_tip.x * width
                )

                middle_y = int(
                    middle_tip.y * height
                )

                ring_x = int(
                    ring_tip.x * width
                )

                ring_y = int(
                    ring_tip.y * height
                )


                detected_hands.append(
                    {
                        "label": hand_label,
                        "confidence": confidence,

                        "index_x": index_x,
                        "index_y": index_y,

                        "thumb_x": thumb_x,
                        "thumb_y": thumb_y,

                        "middle_x": middle_x,
                        "middle_y": middle_y,

                        "ring_x": ring_x,
                        "ring_y": ring_y,
                    }
                )


                # ==================================================
                # DRAW HAND
                # ==================================================

                for start, end in HAND_CONNECTIONS:

                    x1 = int(
                        landmarks[start].x
                        * width
                    )

                    y1 = int(
                        landmarks[start].y
                        * height
                    )

                    x2 = int(
                        landmarks[end].x
                        * width
                    )

                    y2 = int(
                        landmarks[end].y
                        * height
                    )

                    cv2.line(
                        display_frame,
                        (x1, y1),
                        (x2, y2),
                        (255, 255, 255),
                        2
                    )


                for landmark in landmarks:

                    x = int(
                        landmark.x * width
                    )

                    y = int(
                        landmark.y * height
                    )

                    cv2.circle(
                        display_frame,
                        (x, y),
                        4,
                        (0, 255, 0),
                        -1
                    )


                cv2.circle(
                    display_frame,
                    (index_x, index_y),
                    10,
                    (255, 0, 0),
                    -1
                )

                cv2.circle(
                    display_frame,
                    (thumb_x, thumb_y),
                    9,
                    (0, 255, 255),
                    -1
                )

                cv2.circle(
                    display_frame,
                    (middle_x, middle_y),
                    9,
                    (0, 0, 255),
                    -1
                )

                cv2.circle(
                    display_frame,
                    (ring_x, ring_y),
                    9,
                    (255, 0, 255),
                    -1
                )


                # ==================================================
                # ONLY SELECTED HAND CONTROLS SYSTEM
                # ==================================================

                if hand_index != selected_index:
                    continue


                # --------------------------------------------------
                # Save selected-hand position for UI.
                #
                # The X coordinate is converted later for the
                # mirrored display.
                # --------------------------------------------------

                display_hand_active = True


                # ==================================================
                # FINGER POSTURE
                # ==================================================

                index_extended = finger_is_extended(
                    landmarks,
                    8,
                    6,
                    width,
                    height
                )

                middle_extended = finger_is_extended(
                    landmarks,
                    12,
                    10,
                    width,
                    height
                )

                ring_extended = finger_is_extended(
                    landmarks,
                    16,
                    14,
                    width,
                    height
                )

                pinky_extended = finger_is_extended(
                    landmarks,
                    20,
                    18,
                    width,
                    height
                )


                # ==================================================
                # DISTANCES
                # ==================================================

                index_middle_distance = landmark_distance(
                    landmarks[8],
                    landmarks[12],
                    width,
                    height
                )

                index_thumb_distance = landmark_distance(
                    landmarks[8],
                    landmarks[4],
                    width,
                    height
                )

                thumb_middle_distance = landmark_distance(
                    landmarks[4],
                    landmarks[12],
                    width,
                    height
                )

                thumb_ring_distance = landmark_distance(
                    landmarks[4],
                    landmarks[16],
                    width,
                    height
                )


                # ==================================================
                # GESTURE CLASSIFICATION
                #
                # IMPORTANT:
                # Gesture priority remains unchanged.
                # ==================================================

                gesture = "NONE"


                # ==================================================
                # ACTIVE NORMAL / THREE-FINGER PINCH
                # ==================================================

                if pinch_active:

                    if pinch_gesture_type == "THREE_FINGER":

                        gesture = "THREE_FINGER_PINCH"

                    else:

                        gesture = "PINCH"


                # ==================================================
                # ACTIVE RIGHT CLICK
                # ==================================================

                elif right_click_active:

                    gesture = "RIGHT_CLICK"


                # ==================================================
                # THREE-FINGER PINCH
                #
                # THUMB + INDEX + MIDDLE
                # ==================================================

                elif (
                    index_thumb_distance
                    <= THREE_FINGER_PINCH_START_DISTANCE

                    and
                    thumb_middle_distance
                    <= THREE_FINGER_PINCH_START_DISTANCE

                    and not ring_extended
                    and not pinky_extended
                ):

                    gesture = "THREE_FINGER_PINCH"


                # ==================================================
                # RIGHT CLICK
                #
                # THUMB + RING
                # ==================================================

                elif (
                    thumb_ring_distance
                    <= RIGHT_CLICK_START_DISTANCE

                    and not middle_extended
                    and not pinky_extended

                    and index_thumb_distance
                    > PINCH_START_DISTANCE
                ):

                    gesture = "RIGHT_CLICK"


                # ==================================================
                # SCROLL
                #
                # INDEX + MIDDLE
                # ==================================================

                elif (
                    index_extended
                    and middle_extended
                    and not ring_extended
                    and not pinky_extended

                    and index_middle_distance
                    < SCROLL_FINGER_DISTANCE
                ):

                    gesture = "SCROLL"


                # ==================================================
                # NORMAL PINCH
                #
                # THUMB + INDEX
                # ==================================================

                elif (
                    index_thumb_distance
                    <= PINCH_START_DISTANCE

                    and
                    thumb_middle_distance
                    > THREE_FINGER_PINCH_START_DISTANCE

                    and not ring_extended
                    and not pinky_extended
                ):

                    gesture = "PINCH"


                # ==================================================
                # POINTER
                # ==================================================

                elif (
                    index_extended
                    and not middle_extended
                    and not ring_extended
                    and not pinky_extended

                    and index_thumb_distance
                    > PINCH_RELEASE_DISTANCE
                ):

                    gesture = "POINTER"


                # ==================================================
                # NONE
                # ==================================================

                else:

                    gesture = "NONE"


                # ==================================================
                # SAVE DISPLAY GESTURE
                #
                # IMPORTANT:
                # We do NOT draw this text here anymore.
                #
                # It will be drawn AFTER cv2.flip() so it remains
                # readable.
                # ==================================================

                display_gesture = gesture

                display_index_x = index_x
                display_index_y = index_y


                # ==================================================
                # ACTIVE PINCH
                # ==================================================

                if pinch_active:

                    reset_hold_timer()

                    pinch_candidate_frames = 0


                    # ------------------------------------------------
                    # LOCKED POINTER
                    #
                    # Locked pointer always performs SINGLE CLICK.
                    # ------------------------------------------------

                    if pinch_was_locked:

                        if (
                            index_thumb_distance
                            > PINCH_RELEASE_DISTANCE
                        ):

                            complete_pinch_release()

                        continue


                    # ==================================================
                    # THREE-FINGER PINCH
                    #
                    # NEVER DRAGS.
                    # ==================================================

                    if (
                        pinch_gesture_type
                        == "THREE_FINGER"
                    ):

                        if (
                            index_thumb_distance
                            > THREE_FINGER_PINCH_RELEASE_DISTANCE

                            and
                            thumb_middle_distance
                            > THREE_FINGER_PINCH_RELEASE_DISTANCE
                        ):

                            complete_pinch_release()

                        continue


                    # ==================================================
                    # NORMAL PINCH
                    #
                    # ONLY THIS TYPE CAN DRAG.
                    # ==================================================

                    if (
                        pinch_gesture_type
                        == "NORMAL"
                    ):

                        # --------------------------------------------
                        # CHECK MOVEMENT FOR DRAG
                        # --------------------------------------------

                        if (
                            pinch_start_x is not None
                            and not pinch_drag_started
                        ):

                            movement = math.sqrt(
                                (
                                    index_x
                                    - pinch_start_x
                                ) ** 2
                                +
                                (
                                    index_y
                                    - pinch_start_y
                                ) ** 2
                            )


                            # ----------------------------------------
                            # MOVEMENT -> DRAG
                            # ----------------------------------------

                            if (
                                movement
                                >= DRAG_MOVEMENT_THRESHOLD
                            ):

                                pointer.start_drag()

                                pinch_drag_started = True

                                print(
                                    "[GESTURE] "
                                    "NORMAL PINCH MOVEMENT "
                                    "-> DRAG"
                                )


                        # --------------------------------------------
                        # UPDATE DRAG
                        # --------------------------------------------

                        if (
                            pinch_drag_started
                            and pointer.is_dragging()
                        ):

                            pointer.update_drag(
                                index_x,
                                index_y
                            )


                        # --------------------------------------------
                        # NORMAL PINCH RELEASE
                        # --------------------------------------------

                        if (
                            index_thumb_distance
                            > PINCH_RELEASE_DISTANCE
                        ):

                            complete_pinch_release()

                        continue


                    # ------------------------------------------------
                    # SAFETY
                    # ------------------------------------------------

                    continue


                # ==================================================
                # RIGHT CLICK
                # ==================================================

                if gesture == "RIGHT_CLICK":

                    reset_hold_timer()

                    pinch_candidate_frames = 0


                    # ------------------------------------------------
                    # RIGHT CLICK ALREADY ACTIVE
                    # ------------------------------------------------

                    if right_click_active:

                        if (
                            thumb_ring_distance
                            > RIGHT_CLICK_RELEASE_DISTANCE
                        ):

                            reset_right_click_state()

                            print(
                                "[GESTURE] "
                                "RIGHT CLICK RELEASED"
                            )

                        continue


                    # ------------------------------------------------
                    # NEW RIGHT CLICK
                    # ------------------------------------------------

                    right_click_candidate_frames += 1


                    if (
                        right_click_candidate_frames
                        >= RIGHT_CLICK_CONFIRM_FRAMES
                    ):

                        right_click_active = True

                        right_click_candidate_frames = 0

                        pointer.right_click()

                        print(
                            "[GESTURE] "
                            "THUMB + RING "
                            "-> RIGHT CLICK"
                        )

                    continue


                # ==================================================
                # RESET RIGHT CLICK CANDIDATE
                # ==================================================

                right_click_candidate_frames = 0


                # ==================================================
                # SCROLL
                # ==================================================

                if gesture == "SCROLL":

                    if pointer.is_dragging():
                        continue

                    reset_hold_timer()

                    if pointer.is_locked():

                        pointer.unlock()

                    pointer.scroll(
                        index_y
                    )

                    continue


                # ==================================================
                # RESET SCROLL
                # ==================================================

                pointer.reset_scroll()


                # ==================================================
                # NEW THREE-FINGER / NORMAL PINCH
                # ==============================================================

                if (
                    gesture == "PINCH"
                    or
                    gesture == "THREE_FINGER_PINCH"
                ):

                    reset_hold_timer()


                    # ------------------------------------------------
                    # CANDIDATE GESTURE TYPE
                    # ------------------------------------------------

                    if (
                        gesture
                        == "THREE_FINGER_PINCH"
                    ):

                        candidate_type = (
                            "THREE_FINGER"
                        )

                    else:

                        candidate_type = (
                            "NORMAL"
                        )


                    # ------------------------------------------------
                    # START / CONTINUE CANDIDATE
                    # ------------------------------------------------

                    if pinch_candidate_frames == 0:

                        pinch_gesture_type = (
                            candidate_type
                        )

                        pinch_candidate_frames = 1

                    elif (
                        pinch_gesture_type
                        == candidate_type
                    ):

                        pinch_candidate_frames += 1

                    else:

                        pinch_gesture_type = (
                            candidate_type
                        )

                        pinch_candidate_frames = 1


                    # ------------------------------------------------
                    # CONFIRM
                    # ------------------------------------------------

                    if (
                        pinch_candidate_frames
                        >= PINCH_CONFIRM_FRAMES
                    ):

                        pinch_active = True

                        pinch_candidate_frames = 0

                        pinch_start_x = index_x
                        pinch_start_y = index_y

                        pinch_was_locked = (
                            pointer.is_locked()
                        )

                        pinch_drag_started = False


                        # ------------------------------------------------
                        # THREE-FINGER PINCH CONFIRMED
                        # ------------------------------------------------

                        if (
                            pinch_gesture_type
                            == "THREE_FINGER"
                        ):

                            print(
                                "[GESTURE] "
                                "THREE-FINGER PINCH "
                                "CONFIRMED"
                            )

                        else:

                            print(
                                "[GESTURE] "
                                "NORMAL PINCH "
                                "CONFIRMED"
                            )


                        # ------------------------------------------------
                        # LOCKED POINTER
                        #
                        # Always single click.
                        # ------------------------------------------------

                        if pinch_was_locked:

                            pointer.click()

                            pointer.unlock()

                            print(
                                "[GESTURE] "
                                "LOCKED PINCH CLICK COMPLETE"
                            )

                            reset_pinch_state()


                    continue


                # ==================================================
                # POINTER
                # ==================================================

                if gesture == "POINTER":

                    pinch_candidate_frames = 0

                    pinch_gesture_type = None


                    if not pointer.is_locked():

                        if hold_reference_x is None:

                            hold_reference_x = index_x
                            hold_reference_y = index_y

                            hold_start_time = time.time()

                        else:

                            movement = math.sqrt(
                                (
                                    index_x
                                    - hold_reference_x
                                ) ** 2
                                +
                                (
                                    index_y
                                    - hold_reference_y
                                ) ** 2
                            )


                            # -----------------------------------------
                            # FINGER MOVED
                            # -----------------------------------------

                            if (
                                movement
                                > POINTER_HOLD_MOVEMENT_THRESHOLD
                            ):

                                hold_reference_x = index_x
                                hold_reference_y = index_y

                                hold_start_time = (
                                    time.time()
                                )


                            # -----------------------------------------
                            # STATIONARY
                            # -----------------------------------------

                            else:

                                elapsed = (
                                    time.time()
                                    - hold_start_time
                                )

                                if (
                                    elapsed
                                    >= POINTER_HOLD_TIME
                                ):

                                    pointer.lock()

                                    print(
                                        "[GESTURE] "
                                        "1.5 SECOND HOLD CONFIRMED"
                                    )

                                    print(
                                        "[GESTURE] "
                                        "CURSOR LOCKED - "
                                        "PINCH TO CLICK"
                                    )

                                    reset_hold_timer()


                        pointer.move(
                            index_x,
                            index_y
                        )


                    continue


                # ==================================================
                # NONE
                # ==================================================

                if gesture == "NONE":

                    reset_hold_timer()

                    pinch_candidate_frames = 0

                    pinch_gesture_type = None

                    if pointer.is_locked():

                        pointer.unlock()


        # ==========================================================
        # NO HAND
        # ==========================================================

        else:

            if pointer.is_dragging():

                pointer.end_drag()

            pointer.reset()

            reset_pinch_state()

            reset_right_click_state()

            reset_hold_timer()


        # ==========================================================
        # MIRROR DISPLAY ONLY
        #
        # IMPORTANT:
        # All UI text is drawn AFTER this.
        #
        # Therefore text stays upright.
        # ==============================================================

        display_frame = cv2.flip(
            display_frame,
            1
        )


        # ==========================================================
        # CONVERT SELECTED HAND POSITION FOR MIRRORED DISPLAY
        #
        # The camera input remains ORIGINAL.
        # Only the displayed X coordinate is mirrored.
        # ==============================================================

        if display_hand_active:

            display_index_x = (
                width - display_index_x
            )


        # ==========================================================
        # HEADER
        # ==============================================================

        cv2.rectangle(
            display_frame,
            (0, 0),
            (width, 85),
            (25, 25, 25),
            -1
        )


        cv2.putText(
            display_frame,
            "AirTouchOS",
            (25, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.9,
            (0, 255, 255),
            2
        )


        # ----------------------------------------------------------
        # UPDATED INSTRUCTION BAR
        #
        # Scroll has been added.
        # ==============================================================

        cv2.putText(
            display_frame,
            "INDEX = POINTER | "
            "PINCH = CLICK | "
            "3-FINGER PINCH = DOUBLE CLICK | "
            "THUMB+RING = RIGHT CLICK | "
            "INDEX+MIDDLE = SCROLL",
            (25, 67),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.32,
            (220, 220, 220),
            1
        )


        # ==========================================================
        # HAND INFORMATION
        # ==============================================================

        if detected_hands:

            for hand_index, hand in enumerate(
                detected_hands
            ):

                y_position = (
                    120
                    + hand_index * 65
                )

                text = (
                    f'{hand["label"]} Hand | '
                    f'{hand["confidence"]:.2f}'
                )

                cv2.putText(
                    display_frame,
                    text,
                    (25, y_position),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2
                )

        else:

            cv2.putText(
                display_frame,
                "No hand detected",
                (25, 120),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )


        # ==========================================================
        # DYNAMIC GESTURE TEXT
        #
        # IMPORTANT:
        # This section is AFTER cv2.flip().
        #
        # Therefore these texts are NOT mirrored.
        # ==============================================================

        if display_hand_active:

            # ------------------------------------------------------
            # GESTURE STATUS
            # ------------------------------------------------------

            cv2.putText(
                display_frame,
                f"GESTURE: {display_gesture}",
                (width - 210, 200),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 255, 255),
                2
            )


            # ------------------------------------------------------
            # POSITION NEXT TO INDEX FINGER
            # ------------------------------------------------------

            label_x = display_index_x + 15
            label_y = display_index_y

            # Keep label inside right side of screen.
            if label_x > width - 250:

                label_x = (
                    display_index_x - 240
                )

            if label_x < 10:

                label_x = 10

            if label_y < 30:

                label_y = 30

            if label_y > height - 60:

                label_y = height - 60


            # ------------------------------------------------------
            # POINTER
            # ------------------------------------------------------

            if display_gesture == "POINTER":

                cv2.putText(
                    display_frame,
                    "POINTER",
                    (
                        label_x,
                        label_y
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 0),
                    2
                )


            # ------------------------------------------------------
            # NORMAL PINCH
            # ------------------------------------------------------

            elif display_gesture == "PINCH":

                cv2.putText(
                    display_frame,
                    "PINCH",
                    (
                        label_x,
                        label_y
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 255),
                    2
                )


            # ------------------------------------------------------
            # THREE-FINGER PINCH
            # ------------------------------------------------------

            elif (
                display_gesture
                == "THREE_FINGER_PINCH"
            ):

                cv2.putText(
                    display_frame,
                    "DOUBLE CLICK PINCH",
                    (
                        label_x,
                        label_y
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.55,
                    (0, 255, 255),
                    2
                )


            # ------------------------------------------------------
            # RIGHT CLICK
            # ------------------------------------------------------

            elif display_gesture == "RIGHT_CLICK":

                cv2.putText(
                    display_frame,
                    "RIGHT CLICK",
                    (
                        label_x,
                        label_y
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 0, 255),
                    2
                )


            # ------------------------------------------------------
            # SCROLL
            # ------------------------------------------------------

            elif display_gesture == "SCROLL":

                cv2.putText(
                    display_frame,
                    "SCROLL",
                    (
                        label_x,
                        label_y
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.65,
                    (0, 255, 255),
                    2
                )


            # ------------------------------------------------------
            # NONE
            # ------------------------------------------------------

            elif display_gesture == "NONE":

                cv2.putText(
                    display_frame,
                    "NO GESTURE",
                    (
                        25,
                        250
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 0, 255),
                    2
                )


        # ==========================================================
        # LOCKED POINTER STATUS
        #
        # Draw AFTER flip so it remains readable.
        # ==============================================================

        if (
            display_hand_active
            and pointer.is_locked()
        ):

            cv2.putText(
                display_frame,
                "CURSOR LOCKED",
                (25, 250),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 255),
                2
            )

            cv2.putText(
                display_frame,
                "PINCH TO CLICK",
                (25, 280),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2
            )


        # ==========================================================
        # HOLD TIMER
        #
        # UNCHANGED 1.5 SECOND HOLD LOGIC.
        # ==============================================================

        if (
            hold_start_time is not None
            and not pointer.is_locked()
        ):

            elapsed = (
                time.time()
                - hold_start_time
            )

            remaining = max(
                0.0,
                POINTER_HOLD_TIME
                - elapsed
            )

            cv2.putText(
                display_frame,
                f"HOLD: {remaining:.1f}s",
                (25, 315),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 255),
                2
            )


        # ==========================================================
        # DRAG STATUS
        # ==============================================================

        if pointer.is_dragging():

            cv2.putText(
                display_frame,
                "DRAGGING - RELEASE PINCH TO DROP",
                (25, 350),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )


        # ==========================================================
        # RIGHT CLICK STATUS
        # ==============================================================

        if right_click_active:

            cv2.putText(
                display_frame,
                "RIGHT CLICK ACTIVE",
                (25, 385),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 0, 255),
                2
            )


        # ==========================================================
        # STATUS BAR
        # ==============================================================

        cv2.rectangle(
            display_frame,
            (0, height - 45),
            (width, height),
            (25, 25, 25),
            -1
        )


        cv2.putText(
            display_frame,
            "Camera: ACTIVE",
            (20, height - 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1
        )


        cv2.putText(
            display_frame,
            "Pointer: ACTIVE",
            (180, height - 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1
        )


        if pointer.is_locked():

            cv2.putText(
                display_frame,
                "LOCKED",
                (340, height - 16),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 255),
                1
            )

        else:

            cv2.putText(
                display_frame,
                "UNLOCKED",
                (340, height - 16),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                1
            )


        cv2.putText(
            display_frame,
            "Q = Quit",
            (width - 100, height - 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (220, 220, 220),
            1
        )


        # ==========================================================
        # SHOW
        # ==============================================================

        cv2.imshow(
            "AirTouchOS - Touchless Controller",
            display_frame
        )


        # ==========================================================
        # QUIT
        # ==============================================================

        if cv2.waitKey(1) & 0xFF in (ord("q"), ord("Q")):

            break


# ==============================================================
# CLEANUP
# ==============================================================

finally:

    pointer.reset()

    cap.release()

    cv2.destroyAllWindows()

    landmarker.close()

    print(
        "AirTouchOS stopped."
    )