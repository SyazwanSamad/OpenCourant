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
! OpenReader rejects structured meshes during loading; retain this defensive Starter check.
module hm_s_ale_mod
  implicit none
contains
  subroutine hm_s_ale(nsubmod,lsubmodel,input_modification)
    use submodel_mod, only : submodel_data
    use input_modification_mod, only : input_modif_
    integer, intent(in) :: nsubmod
    type(submodel_data), intent(in) :: lsubmodel(nsubmod)
    type(input_modif_), intent(inout) :: input_modification
    integer :: count
    call hm_option_count('/ALE/STRUCTURED_MESH', count)
    if(count /= 0) then
      write(*,'(A)') 'ERROR: /ALE/STRUCTURED_MESH is unsupported by OpenReader.'
      call arret(2)
      return
    endif
    input_modification%s_ale_nb = 0
    allocate(input_modification%s_ale(0))
  end subroutine hm_s_ale
end module hm_s_ale_mod
