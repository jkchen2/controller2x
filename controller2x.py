import pathlib
import struct
import sys
import subprocess
import time
import yaml

from collections import defaultdict


CATEGORY_KEYS = {
    1: 'buttons',
    2: 'axis'
}

AXIS_KEYS = {
    -1: 'max',
    1: 'min'
}


def main(config_path, device_path='/dev/input/js0', config_name='global'):
    path = pathlib.Path(config_path)
    if not path.exists():
        print("Cannot find config file", file=sys.stderr)
        return 1

    # Read configuration file
    with path.open('r') as config_file:
        config = yaml.load(config_file)
        active_config = config['configurations'][config_name]

    # Check if the device is available
    device = pathlib.Path(device_path)
    if not device.exists():
        print("Device not connected", file=sys.stderr)
        return 1

    # Set valid buttons
    valid_buttons = set()
    for key, value in CATEGORY_KEYS.items():
        for button_index in active_config.get(value, {}).keys():
            valid_buttons.add('{}:{}'.format(key, button_index))

    buttons = defaultdict(bool)
    while True:

        # Wait until device is available if disconnected
        backoff = 0
        while not device.exists():
            if backoff > 2:
                print("Device connection retry timed out. Exiting.", file=sys.stderr)
                return 1
            backoff += 0.025
            print('sleeping for {} seconds'.format(backoff))
            time.sleep(backoff)
        print("Reading inputs...")

        # Read input
        with device.open('rb') as device_file:
            while True:
                try:
                    data = device_file.read(8)
                except OSError:
                    print("Device was disconnected!", file=sys.stderr)
                    time.sleep(1)
                    break
                pressed, intensity, category, index = struct.unpack('8b', data)[4:]
                key = '{}:{}'.format(category, index)
                if key not in valid_buttons:  # Skip unconfigured buttons
                    continue

                last_press = buttons[key]
                if last_press != 0 and pressed == 0:  # Button up
                    action = active_config[CATEGORY_KEYS[category]][index]
                    if 'min' in action or 'max' in action:  # Axis
                        action = action[AXIS_KEYS[last_press]]

                    print("Action {0[type]}: {0[value]}".format(action))
                    action_type = action['type']
                    if action_type == 'key':
                        subprocess.run(['xdotool', 'key', action['value']])
                    elif action_type == 'command':
                        subprocess.Popen(action['value'])

                buttons[key] = pressed


if __name__ == '__main__':
    args = sys.argv
    if len(args) != 2:
        print("Usage:\n\tpython3 controller2x.py <config file>", file=sys.stderr)
        sys.exit(1)
    sys.exit(main(args[1]))
