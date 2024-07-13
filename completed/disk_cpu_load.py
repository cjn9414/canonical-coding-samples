#!/usr/local/bin/python3

import argparse
import re
import pathlib

# Script to test CPU load imposed by a simple disk read operation
#
# Authors
#   Carter Nesbitt <ccnesbitt@gmail.com>
#
# The purpose of this script is to run disk stress tests using the
# stress-ng program.
#
# Usage:
#   disk_cpu_load.py [ --max-load <load> ] [ --xfer <mebibytes> ]
#                    [ --verbose ] [ <device-filename> ]
#
# Parameters:
#  --max-load <load> -- The maximum acceptable CPU load, as a percentage.
#                       Defaults to 30.
#  --xfer <mebibytes> -- The amount of data to read from the disk, in
#                        mebibytes. Defaults to 4096 (4 GiB).
#  --verbose -- If present, produce more verbose output
#  <device-filename> -- This is the WHOLE-DISK device filename (with or
#                       without "/dev/"), e.g. "sda" or "/dev/sda". The
#                       script finds a filesystem on that device, mounts
#                       it if necessary, and runs the tests on that mounted
#                       filesystem. Defaults to /dev/sda.


def fetch_stat(stat_file="/proc/stat"):
    """Fetch CPU utilization data from stat file with /proc/stat syntax"""

    with open(stat_file, 'r') as fd:
        lines = fd.readlines()

    for words in [line.strip().split() for line in lines]:
        if words[0] == "cpu":
            return [int(num) for num in words[1:]]

    raise OSError(f"Can not read CPU utilization from {stat_file}!")


def compute_cpu_load(start_stat, end_stat, verbose):
    """Calculate CPU utilzation (percentage of non-idle CPU usage)"""

    total_start, total_end = sum(start_stat), sum(end_stat)

    diff_idle = end_stat[3] - start_stat[3]
    diff_total = total_end - total_start
    diff_used = diff_total - diff_idle

    if verbose:
        print(f"Start CPU time = {total_start}")
        print(f"End CPU time = {total_end}")
        print(f"CPU time used = {diff_used}")
        print(f"Total elapsed time = {diff_total}")

    if diff_total == 0:
        return 0

    return (diff_used * 100) / diff_total


def main():
    parser = argparse.ArgumentParser(
        prog="disk_cpu_load",
        description="Performs disk stress test by reading data from a disk, \
                with a maximum acceptable CPU load"
    )

    parser.add_argument(
        "--max-load",
        action="store",
        default=30,
        type=int,
        help="The maximum acceptable CPU load, as a percentage"
    )

    parser.add_argument(
        "--xfer",
        action="store",
        default=4096,
        type=int,
        help="The amount of data to read from the disk, in mebibytes"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="If present, produce more verbose output", required=False
    )

    # Compile / verify arguments, and fetch disk path if provided
    args, disk = parser.parse_known_args()

    if len(disk) == 0:
        disk = "/dev/sda"
    elif len(disk) > 1:
        print(f"ERROR: Unknown positional arguments: {disk[1:]}")
    else:
        disk = disk[0]

    # Ensure disk path is prefixed with "/dev" root sub-directory
    if not re.search(r"^/dev/", disk):
        disk = f"/dev/{disk}"

    # Exit gracefully if the provided path is not a block device
    if not pathlib.Path(disk).is_block_device():
        print(f'Unknown block device "{disk}"')
        return 1

    print(f"Testing CPU load when reading {args.xfer} MiB from {disk}")
    print(f"Maximum acceptable CPU load is {args.max_load}")

    block_size = 2**20

    # Wrap reading operation wth CPU stat fetch
    start_cpu = fetch_stat()

    print("Beginning disk read....")

    with open(disk, 'rb') as fd:
        fd.flush()
        for _ in range(args.xfer):
            fd.read(block_size)

    print("Disk read complete!")

    # Wrap reading operation wth CPU stat fetch
    end_cpu = fetch_stat()

    cpu_load = compute_cpu_load(start_cpu, end_cpu, args.verbose)

    print(f"Detected disk read CPU load is {int(cpu_load)}")

    # Final CPU load check
    if (cpu_load > args.max_load):
        print("*** DISK CPU LOAD TEST HAS FAILED! ***")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())
