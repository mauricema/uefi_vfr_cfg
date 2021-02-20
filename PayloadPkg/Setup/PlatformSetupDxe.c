/** @file

  Copyright (c) 2004  - 2019, Intel Corporation. All rights reserved.<BR>

  SPDX-License-Identifier: BSD-2-Clause-Patent

**/

#include <Uefi.h>

EFI_BOOT_SERVICES  *gBS         = NULL;

EFI_SYSTEM_TABLE   *gST         = NULL;

EFI_HANDLE         gImageHandle = NULL;

VOID               *_ModuleEntryPoint;

EFI_STATUS
EFIAPI
PlatformSetupDxeInit (
  IN EFI_HANDLE         ImageHandle,
  IN EFI_SYSTEM_TABLE   *SystemTable
  )
{
  return EFI_SUCCESS;
}