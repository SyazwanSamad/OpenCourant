!Copyright>        OpenRadioss
!Copyright>        Copyright (C) 2026 Siemens
!Copyright>
!Copyright>        This program is free software: you can redistribute it and/or modify
!Copyright>        it under the terms of the GNU Affero General Public License as published by
!Copyright>        the Free Software Foundation, either version 3 of the License, or
!Copyright>        (at your option) any later version.
!Copyright>
!Copyright>        This program is distributed in the hope that it will be useful,
!Copyright>        but WITHOUT ANY WARRANTY; without even the implied warranty of
!Copyright>        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
!Copyright>        GNU Affero General Public License for more details.
!Copyright>
!Copyright>        You should have received a copy of the GNU Affero General Public License
!Copyright>        along with this program.  If not, see <https://www.gnu.org/licenses/>.
!Copyright>
!Copyright>
!Copyright>        OpenCourant
!Copyright>        Copyright (C) 2026 OpenCourant contributors
!Copyright>
!Copyright>        Modified by the OpenCourant project, 2026.
!Copyright>        Modifications are licensed under the GNU Affero General Public
!Copyright>        License, version 3 or (at your option) any later version.
!Copyright>
!Copyright>        This file is part of OpenCourant, a fork of OpenRadioss.
!Copyright>        See COPYRIGHT.md at the root of the repository for the full
!Copyright>        copyright and attribution statement.
!||====================================================================
!||    hm_is_part_with_elements_mod   ../starter/source/devtools/reader/hm_is_part_with_elements.F90
!||--- called by ------------------------------------------------------
!||    hm_read_part                   ../starter/source/model/assembling/hm_read_part.F
!||====================================================================
        module hm_is_part_with_elements_mod
         use, intrinsic :: iso_c_binding, only : c_bool
         implicit none
      contains
! ======================================================================================================================
!                                                   procedures
! ======================================================================================================================
!! \brief check if a /PART has elements
!! \details This routine checks if a /PART has elements.
!||====================================================================
!||    hm_is_part_with_elements    ../starter/source/devtools/reader/hm_is_part_with_elements.F90
!||--- called by ------------------------------------------------------
!||    hm_read_part                ../starter/source/model/assembling/hm_read_part.F
!||--- calls      -----------------------------------------------------
!||====================================================================
        subroutine hm_is_part_with_elements(part_id, is_part_with_elements)
! ----------------------------------------------------------------------------------------------------------------------
!                                                   Modules
! ----------------------------------------------------------------------------------------------------------------------
! ----------------------------------------------------------------------------------------------------------------------
!                                                   Implicit none
! ----------------------------------------------------------------------------------------------------------------------
          implicit none
! ----------------------------------------------------------------------------------------------------------------------
!                                                   Arguments
! ----------------------------------------------------------------------------------------------------------------------
          integer, intent(in) :: part_id
          logical(c_bool), intent(inout) :: is_part_with_elements
! ----------------------------------------------------------------------------------------------------------------------
! ----------------------------------------------------------------------------------------------------------------------
!                                                   Body
! ----------------------------------------------------------------------------------------------------------------------
          call cpp_is_part_with_elements(part_id, is_part_with_elements)
! ----------------------------------------------------------------------------------------------------------------------
        end subroutine hm_is_part_with_elements
      end module hm_is_part_with_elements_mod
