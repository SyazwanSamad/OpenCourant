!Copyright>        OpenCourant
!Copyright>        Copyright (C) 2026 OpenCourant contributors
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
!Copyright>        This file is part of OpenCourant, a fork of OpenRadioss.
!Copyright>        See COPYRIGHT.md at the root of the repository for the full
!Copyright>        copyright and attribution statement.
program guard_driver
  use, intrinsic :: iso_c_binding, only : c_int, c_char
  use hm_evaluate_rbodies_from_rigid_parts_mod
  implicit none
  interface
    subroutine initialize(result, version) bind(C, name='hm_reader_variables')
      import c_int
      integer(c_int) :: result, version
    end subroutine
    subroutine load_model(name, size, result, includes, path, path_size) bind(C, name='cpp_build_model_inc')
      import c_int, c_char
      character(kind=c_char) :: name(*), path(*)
      integer(c_int) :: size, result, includes, path_size
    end subroutine
    subroutine count_parts(kind, size, count) bind(C, name='cpp_option_count')
      import c_int, c_char
      character(kind=c_char) :: kind(*)
      integer(c_int) :: size, count
    end subroutine
  end interface
  character(4096) :: filename
  integer(c_int) :: result, version, includes, npart, length, path_size, kind_size
  integer, allocatable :: counts(:)
  call get_command_argument(1, filename)
  version = 2612
  result = 0
  call initialize(result, version)
  if (result /= 0) stop 10
  includes = 0
  length = len_trim(filename)
  path_size = 0
  call load_model(filename, length, result, includes, '', path_size)
  if (result /= 0) stop 11
  kind_size = 4
  call count_parts('PART', kind_size, npart)
  allocate(counts(npart))
  counts = -1
  call hm_evaluate_rbodies_from_rigid_parts(npart, counts)
  if (any(counts /= 0)) stop 12
  print '(A)', 'guard accepted ordinary parts'
end program

! Exercise the production guard without linking the rest of Starter.
subroutine arret(code)
  implicit none
  integer, intent(in) :: code
  if (code /= 2) stop 13
  stop 2
end subroutine
