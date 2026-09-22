"""L298N assignments from the existing XEMO ESP32 DevKit wiring."""
MOTOR_PINS = {1: (26, 19, 18), 3: (27, 17, 16)}
INVERT = {1: False, 3: False}
WIRE_FORWARD_SIGN = {1: -1, 3: 1}
PWM_FREQ = 1500
MAX_DUTY = 0.45
MIN_DUTY = 0.20
DEADBAND_DEG = 4
SLEW_PER_S = 3.0
# Legacy growbot.dev /ws gait has no wheel-mode bit. Preserve a small residual
# yaw but turn its mirrored leg oscillation into forward throttle in firmware.
GAIT_YAW_DAMP = 0.20
DEADMAN_MS = 500
