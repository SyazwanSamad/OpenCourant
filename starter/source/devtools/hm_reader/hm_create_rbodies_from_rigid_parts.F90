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
!||    hm_create_rbodies_from_rigid_parts_mod   ../starter/source/devtools/hm_reader/hm_create_rbodies_from_rigid_parts.F90
!||--- called by ------------------------------------------------------
!||    starter0                                 ../starter/source/starter/starter0.F
!||====================================================================
      module hm_create_rbodies_from_rigid_parts_mod
        use, intrinsic :: iso_c_binding, only : c_int
        implicit none
        interface
          subroutine create_rigid_parts(mapping, ids) bind(C, name='cpp_create_rbodies_from_rigid_parts')
            import c_int
            integer(c_int), intent(out) :: mapping(*), ids(*)
          end subroutine
        end interface
      contains
! ======================================================================================================================
!                                                   procedures
! ======================================================================================================================
!! \brief create /RBODY for RIGID parts (/PART with Irigid)
!! \details This routine create a /RBODY for each /PART with Irigid .
!||====================================================================
!||    hm_create_rbodies_from_rigid_parts    ../starter/source/devtools/hm_reader/hm_create_rbodies_from_rigid_parts.F90
!||--- called by ------------------------------------------------------
!||    starter0                              ../starter/source/starter/starter0.F
!||--- calls      -----------------------------------------------------
!||====================================================================
        subroutine hm_create_rbodies_from_rigid_parts(NB_NEWRBODIES,NEW_RBODY_TO_PART,NEW_RBODY_ID)
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
          integer, intent(in) :: NB_NEWRBODIES
          integer(c_int), dimension(NB_NEWRBODIES), intent(out) :: NEW_RBODY_TO_PART
          integer(c_int), dimension(NB_NEWRBODIES), intent(out) :: NEW_RBODY_ID
! ----------------------------------------------------------------------------------------------------------------------
! ----------------------------------------------------------------------------------------------------------------------
!                                                   Body
! ----------------------------------------------------------------------------------------------------------------------
#ifdef HM_READER_NO_RBODIES_FROM_RIGID_PARTS
          ! Unreachable while hm_evaluate_rbodies_from_rigid_parts forces the
          ! counts to zero; kept as a guard should a caller bypass that path.
          if (NB_NEWRBODIES > 0) then
            write(*,'(A)') 'ERROR: /PART Irigid requires a newer input reader.'
            write(*,'(A)') 'This compatibility build cannot create RBODIES from rigid parts.'
            call arret(2)
          endif
          NEW_RBODY_TO_PART(1:NB_NEWRBODIES) = 0
          NEW_RBODY_ID(1:NB_NEWRBODIES) = 0
#else
          call create_rigid_parts(NEW_RBODY_TO_PART,NEW_RBODY_ID)
#endif
! ----------------------------------------------------------------------------------------------------------------------
        end subroutine hm_create_rbodies_from_rigid_parts

        subroutine hm_rbody_read_order(nbody, nnew, body_ids, new_ids, order)
          integer, intent(in) :: nbody, nnew, body_ids(nbody), new_ids(nnew)
          integer, intent(out) :: order(nbody)
          integer :: i, j, count, positions(nnew)
          positions = 0
          order = 0
          count = 0
          do i = 1, nbody
            do j = 1, nnew
              if (body_ids(i) == new_ids(j)) exit
            enddo
            if (j <= nnew) then
              if (positions(j) /= 0) exit
              positions(j) = i
            else
              count = count + 1
              order(count) = i
            endif
          enddo
          if (i <= nbody .or. count /= nbody-nnew .or. any(positions == 0)) then
            write(*,'(A)') 'ERROR: rigid-body IDs do not match the rigid-part conversion mapping.'
            call arret(2)
            return
          endif
          ! Include order can interleave explicit bodies with generated bodies.
          order(count+1:nbody) = positions
        end subroutine hm_rbody_read_order
      end module hm_create_rbodies_from_rigid_parts_mod
