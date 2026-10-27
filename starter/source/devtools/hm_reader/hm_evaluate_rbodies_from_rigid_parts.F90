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
!||    hm_evaluate_rbodies_from_rigid_parts_mod   ../starter/source/devtools/hm_reader/hm_evaluate_rbodies_from_rigid_parts.F90
!||--- called by ------------------------------------------------------
!||    starter0                                   ../starter/source/starter/starter0.F
!||====================================================================
      module hm_evaluate_rbodies_from_rigid_parts_mod
        use, intrinsic :: iso_c_binding, only : c_int
        implicit none
        interface
          subroutine evaluate_rigid_parts(counts) bind(C, name='cpp_evaluate_rbodies_number_from_rigid_parts')
            import c_int
            integer(c_int), intent(out) :: counts(*)
          end subroutine
        end interface
      contains
! ======================================================================================================================
!                                                   procedures
! ======================================================================================================================
!! \brief create /RBODY for RIGID parts (/PART with Irigid)
!! \details This routine create a /RBODY for each /PART with Irigid .
!||====================================================================
!||    hm_evaluate_rbodies_from_rigid_parts           ../starter/source/devtools/hm_reader/hm_evaluate_rbodies_from_rigid_parts.F90
!||--- called by ------------------------------------------------------
!||    starter0                                       ../starter/source/starter/starter0.F
!||--- calls      -----------------------------------------------------
!||====================================================================
        subroutine hm_evaluate_rbodies_from_rigid_parts(NPART,NBRBODIES_PER_PART)
! ----------------------------------------------------------------------------------------------------------------------
!                                                   Modules
! ----------------------------------------------------------------------------------------------------------------------
#ifdef HM_READER_NO_RBODIES_FROM_RIGID_PARTS
          use, intrinsic :: iso_c_binding, only : c_bool
#endif
! ----------------------------------------------------------------------------------------------------------------------
!                                                   Implicit none
! ----------------------------------------------------------------------------------------------------------------------
          implicit none
! ----------------------------------------------------------------------------------------------------------------------
!                                                   Arguments
! ----------------------------------------------------------------------------------------------------------------------
          integer, intent(in) :: NPART
          integer(c_int), dimension(NPART), intent(out) :: NBRBODIES_PER_PART
#ifdef HM_READER_NO_RBODIES_FROM_RIGID_PARTS
          integer :: i, irigid, part_id, sub_id, value_type
          logical(c_bool) :: available
          external :: cpp_option_start, cpp_option_next, cpp_get_intv, arret
#endif
! ----------------------------------------------------------------------------------------------------------------------
! ----------------------------------------------------------------------------------------------------------------------
!                                                   Body
! ----------------------------------------------------------------------------------------------------------------------
#ifdef HM_READER_NO_RBODIES_FROM_RIGID_PARTS
          ! shortcut: rigid-part conversion is bypassed, enable after integration and numerical validation.
          NBRBODIES_PER_PART(1:NPART) = 0
          call cpp_option_start('PART', 4)
          do i = 1, NPART
            call cpp_option_next()
            irigid = 0
            call cpp_get_intv('IRIGID', 6, irigid, sub_id, available, value_type)
            if (available .and. irigid /= 0) then
              call cpp_get_intv('id', 2, part_id, sub_id, available, value_type)
              write(*,'(A,I0,A,I0,A,I0,A)') 'ERROR: /PART ', part_id, ' (submodel ', sub_id, &
                ') requests IRIGID=', irigid, ', but this reader cannot convert rigid parts to /RBODY.'
              call arret(2)
              return
            endif
          enddo
#else
          call evaluate_rigid_parts(NBRBODIES_PER_PART)
#endif
! ----------------------------------------------------------------------------------------------------------------------
        end subroutine hm_evaluate_rbodies_from_rigid_parts
      end module hm_evaluate_rbodies_from_rigid_parts_mod
