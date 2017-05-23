# Copyright 2016 Daniel Manila
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""This modules contains the code to install the grub2 bootloader."""

from weresync.plugins import IBootPlugin
import weresync.device as device
from weresync.exception import CopyError, DeviceError
import subprocess
import os
import sys
import logging

LOGGER = logging.getLogger(__name__)


class GrubPlugin(IBootPlugin):
    """Plugin to install the grub2 bootloader. Does not install grub legacy."""

    def __init__(self):
        super().__init__("grub2", "Grub2")

    def get_help(self):
        return "Installs the Grub2 bootloader."\
            "This works on both UEFI and MBR systems."

    def install_bootloader(self, source_mnt, target_mnt, copier,
                           excluded_partitions=[],
                           boot_partition=None, root_partition=None,
                           efi_partition=None):
        if root_partition is None:
                for i in copier.target.get_partitions():
                    try:
                        mount_point = copier.target.mount_point(i)
                        if mount_point is None:
                            copier.target.mount_partition(i, target_mnt)
                            mount_point = target_mnt
                        if os.path.exists(mount_point +
                                          ("/" if not mount_point.endswith("/")
                                           else "") + "boot/grub"):
                            root_partition = i
                            break
                        else:
                            copier.target.unmount_partition(i)
                    except DeviceError as ex:
                        LOGGER.warning("Could not mount partition {0}. "
                                       "Assumed to not be the partition grub "
                                       "is on.".format(i))
                        LOGGER.debug("Error info:\n", exc_info=sys.exc_info())
                else:  # No partition found
                    raise CopyError("Could not find partition with "
                                    "'boot/grub' folder on device {0}".format(
                                        copier.target.device))

        mounted_here = False
        boot_mounted_here = False
        efi_mounted_here = False
        try:
            mount_loc = copier.target.mount_point(root_partition)
            if mount_loc is None:
                copier.target.mount_partition(root_partition, target_mnt)
                mounted_here = True
                mount_loc = target_mnt

            mount_loc += "/" if not mount_loc.endswith("/") else ""

            if boot_partition is not None:
                copier.target.mount_partition(boot_partition,
                                              mount_loc + "boot")
                boot_mounted_here = True

            if efi_partition is not None:
                os.makedirs(mount_loc + "boot/efi", exist_ok=True)
                copier.target.mount_partition(efi_partition,
                                              mount_loc + "boot/efi")
                efi_mounted_here = True

            print("Updating Grub")
            grub_cfg = mount_loc + "boot/grub/grub.cfg"
            old_perms = os.stat(grub_cfg)[0]
            try:
                with open(grub_cfg, "r+") as grubcfg:
                    cfg = grubcfg.read()
                    LOGGER.debug("UUID Dicts: " + str(copier.get_uuid_dict()))
                    final = device.multireplace(cfg, copier.get_uuid_dict())
                    grubcfg.seek(0)
                    grubcfg.write(final)
                    grubcfg.truncate()
                    grubcfg.flush()
            finally:
                os.chmod(grub_cfg, old_perms)

            print("Installing Grub")
            grub_command = ["grub-install",
                            "--boot-directory=" + mount_loc + "boot",
                            "--recheck"]
            if efi_partition is not None:
                grub_command += ["--efi-directory=" + mount_loc + "boot/efi",
                                 "--target=x86_64-efi", "--removable"]
            else:
                grub_command += ["--target=i386-pc", copier.target.device]
            LOGGER.debug("Grub command: " + " ".join(grub_command))

            grub_install = subprocess.Popen(grub_command,
                                            stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT)
            install_output, install_error = grub_install.communicate()
            if grub_install.returncode != 0:
                raise DeviceError(copier.target.device,
                                  "Error installing grub.",
                                  str(install_output,
                                      "utf-8"))

            print("Consider running update-grub on your backup. WereSync"
                  " copies can sometimes fail to capture all the nuances of a"
                  " complex system.")
            print("Cleaning up.")
        finally:
            if efi_mounted_here:
                copier.target.unmount_partition(efi_partition)
            if boot_mounted_here:
                copier.target.unmount_partition(boot_partition)
            if mounted_here:
                copier.target.unmount_partition(root_partition)
        print("Finished!")
