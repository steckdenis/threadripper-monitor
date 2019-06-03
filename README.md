# Ryzen Power and CPU Usage Monitor

Most system monitors on Linux have a hard time with 32 cores and 64 threads. This program, made especially for AMD Threadripper processors but also compatible with Desktop Ryzen and EPYC, displays the CPU use of all the cores (and threads), in a nice graphical format that matches the physical implementation of the cores (on EPYC, Threadripper and Ryzen processors with 4, 2 or 1 Zeppelin dies).

## Dependencies

- Python 3
- PyQt5
- PyQtChart
- Linux: `rapl-read-ryzen`
- Windows: `pywin32` and `WMI`

The Python dependencies are installable with `pip`, and come pre-packaged in wheels. RAPL has to be installed from [its Github repository](https://github.com/djselbeck/rapl-read-ryzen).

## Installing RAPL

If it is not yet merged, be sure to use my branch of RAPL, available [here](https://github.com/steckdenis/rapl-read-ryzen). It fixes how SMT interacts with power consumption.

    git clone https://github.com/djselbeck/rapl-read-ryzen.git
    cd rapl-read-ryzen
    gcc -std=c99 -O2 -o rapl ryzen.c -lm
    sudo cp rapl /usr/bin
    sudo chown root:root /usr/bin/rapl
    sudo chmod +s /usr/bin/rapl

The last two lines make RAPL a set-uid root binary. **Be aware of this**, as it can have security implications. RAPL has to be run as root, because it has to access the CPU MSRs. There may be another way of allowing RAPL to be easily run as an user, for instance by changing permissions around, but I did not manage to do that as easily as making RAPL set-uid root.

## Running

Once RAPL and the Python dependencies, the monitor is super easy to use:

    python3 main.py

And you are greeted by a nice GUI with animated graphs of the CPU usage and power consumption. The main area of the window displays the 2 or 4 dies of your CPU, with their two CCXes, each having 2, 3 or 4 cores, each having 2 threads. Threads become darker blue as they are used. A red bar also displays the power usage of individual cores, in addition to the main graph that shows the total power use of the whole package, and all the cores combined.

For **Threadripper WX** variants, the orange dies are connected to memory (NUMA nodes 0 and 2, cores numbered 0 to 16 with Kernel 4.18), while the gray dies are *compute-only*. On **EPYC**, all four dies are supposed to be connected to memory, and are thus displayed in orange.

## Caveats

- Windows support is difficult to achieve and requires extra dependencies (see above). Currently, power consumption monitoring is not supported on Windows.
- The CPU topology is detected by reading `/proc/cpuinfo` (or using WMI on Windows) and matching the name of the CPU. Future CPUs will need this program to be updated.
- This program assumes that SMT is available and used. As such, it does not support the low-end Ryzen 1st gen processors without SMT
- APUs are not yet supported. Some simple changes should be enough to add support for them, as they are basically dies with only one CCX.
