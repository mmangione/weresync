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
"""This modules contains the code to simply translate the UUIDs of all text
files to the new drive. It does not change anything else.

In order to save RAM, uuid_copy will not copy files larger than 200 MB.
This works for many bootloaders."""

from weresync.plugins import IBootPlugin
from weresync.exception import CopyError, DeviceError
import os
import sys
import os.path
import logging
import weresync.plugins as plugins

LOGGER = logging.getLogger(__name__)


class UUIDPlugin(IBootPlugin):

    def __init__(self):
        super().__init__("uuid_copy", "UUID Copy")

    def get_help(self):
        return """Changes all UUIDs in every file of /boot to the new drive's UUIDs.
        \nDoes not install anything else. This is the default option."""

    def install_bootloader(self, source_mnt, target_mnt, copier,
                           excluded_partitions=[],
                           boot_partition=None, root_partition=None,
                           efi_partition=None):

        if root_partition is None and boot_partition is None:
                for i in copier.target.get_partitions():
                    try:
                        mounted_here = False
                        mount_point = copier.target.mount_point(i)
                        if mount_point is None:
                            copier.target.mount_partition(i, target_mnt)
                            mount_point = target_mnt
                            mounted_here = True
                        if os.path.exists(mount_point +
                                          ("/" if not mount_point.endswith("/")
                                           else "") + "boot"):
                            root_partition = i
                            plugins.translate_uuid(copier, i, "/boot",
                                                   target_mnt)
                            break
                    except DeviceError as ex:
                        LOGGER.warning("Could not mount partition {0}. "
                                       "Assumed to not be the partition grub "
                                       "is on.".format(i))
                        LOGGER.debug("Error info:\n", exc_info=sys.exc_info())
                    finally:
                        try:
                            if mounted_here:
                                self.target.unmount_partition(i)
                        except DeviceError as ex:
                            LOGGER.warning("Error unmounting partition " + i)
                            LOGGER.debug("Error info:\n",
                                         exc_info=sys.exc_info())
                else:  # No partition found
                    raise CopyError("Could not find partition with "
                                    "'boot' folder on device {0}".format(
                                        copier.target.device))
        elif boot_partition is not None:
            plugins.translate_uuid(copier, boot_partition, "/", target_mnt)
        else:
            plugins.translate_uuid(copier, root_partition, "/boot", target_mnt)

        if efi_partition is not None:
            plugins.translate_uuid(copier, efi_partition, "/", target_mnt)