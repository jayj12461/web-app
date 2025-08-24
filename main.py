import minimalmodbus
import struct
import time
import json
from database import calc_fault_frequencies, check_fault_matches, get_machine_info, insert_vibration

device_id = 1
machine_id = 1


instrument = minimalmodbus.Instrument('COM8', device_id)  # (พอร์ต, Slave ID)
instrument.serial.baudrate = 9600
instrument.serial.bytesize = 8
instrument.serial.parity   = minimalmodbus.serial.PARITY_NONE
instrument.serial.stopbits = 1
instrument.serial.timeout  = 1


# IEE754
def read_float(register):
    """ อ่านค่า float (2 registers) """
    regs = instrument.read_registers(register, 2, functioncode=3)
    raw = (regs[0] << 16) + regs[1]
    return struct.unpack('>f', raw.to_bytes(4, byteorder='big'))[0]

if __name__ == "__main__":
    
    machine = get_machine_info(machine_id)

    if not machine:
        raise RuntimeError("❌ ไม่พบ machine info")

    fault_freqs = calc_fault_frequencies(machine)
    print(fault_freqs)


    while True:
        # --------- Velocity (mm/s) ---------
        vx = instrument.read_register(0x0001, 1, functioncode=3) / 10.0
        vy = instrument.read_register(0x0002, 1, functioncode=3) / 10.0
        vz = instrument.read_register(0x0003, 1, functioncode=3) / 10.0

        # --------- Acceleration (m/s²) ---------
        ax = instrument.read_register(0x000A, 1, functioncode=3) / 10.0
        ay = instrument.read_register(0x000B, 1, functioncode=3) / 10.0
        az = instrument.read_register(0x000C, 1, functioncode=3) / 10.0

        # --------- Frequency (Hz) ---------
        fx = read_float(0x0021)
        fy = read_float(0x0023)
        fz = read_float(0x0025)

        # --------- Match check ---------
        x_matches = check_fault_matches(fx, fault_freqs)
        y_matches = check_fault_matches(fy, fault_freqs)
        z_matches = check_fault_matches(fz, fault_freqs)

        print(f"X={fx:.2f}Hz → {x_matches}")
        print(f"Y={fy:.2f}Hz → {y_matches}")
        print(f"Z={fz:.2f}Hz → {z_matches}")
        

        print("Velocity  (mm/s): X={:.2f}, Y={:.2f}, Z={:.2f}".format(vx, vy, vz))
        print("Accel.    (m/s²): X={:.2f}, Y={:.2f}, Z={:.2f}".format(ax, ay, az))
        print("Frequency (Hz)  : X={:.2f}, Y={:.2f}, Z={:.2f}".format(fx, fy, fz))
        print("-"*50)

        # --------- Insert raw to DB ---------

        x_matches = json.dumps(x_matches)
        y_matches = json.dumps(y_matches)
        z_matches = json.dumps(z_matches)

        insert_vibration(
            machine_id,
            vx=vx, vy=vy, vz=vz,
            ax=ax, ay=ay, az=az,
            fx=fx, fy=fy, fz=fz,
            x_fault_matches=x_matches , y_fault_matches=y_matches , z_fault_matches=z_matches
        )

        time.sleep(60)