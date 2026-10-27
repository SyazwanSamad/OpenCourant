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
program integration_driver
  use, intrinsic :: iso_c_binding, only : c_int, c_char
  use hm_evaluate_rbodies_from_rigid_parts_mod
  use hm_create_rbodies_from_rigid_parts_mod
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
  integer(c_int) :: result, version, includes, npart, length, path_size, kind_size, total
  integer(c_int), allocatable :: counts(:), mapping(:), ids(:)
  integer :: order(5)
  call hm_rbody_read_order(5, 2, [101, 100, 102, 90, 110], [102, 101], order)
  if (any(order /= [2, 4, 5, 3, 1])) stop 20
  call hm_rbody_read_order(5, 0, [101, 100, 102, 90, 110], [integer::], order)
  if (any(order /= [1, 2, 3, 4, 5])) stop 21
  call get_command_argument(1, filename)
  if (trim(filename) == 'missing-id') then
    call hm_rbody_read_order(5, 1, [101, 100, 102, 90, 110], [999], order)
    stop 22
  endif
  if (trim(filename) == 'duplicate-id') then
    call hm_rbody_read_order(5, 1, [101, 101, 102, 90, 110], [101], order)
    stop 23
  endif
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
  allocate(counts(0:npart+1))
  counts = 123456789
  call hm_evaluate_rbodies_from_rigid_parts(npart, counts(1:npart))
  if (counts(0) /= 123456789 .or. counts(npart+1) /= 123456789) stop 12
  total = sum(counts(1:npart))
  allocate(mapping(0:total+1), ids(0:total+1))
  mapping = 123456789
  ids = 123456789
  call hm_create_rbodies_from_rigid_parts(total, mapping(1:total), ids(1:total))
  if (mapping(0) /= 123456789 .or. mapping(total+1) /= 123456789) stop 13
  if (ids(0) /= 123456789 .or. ids(total+1) /= 123456789) stop 14
  if (any(mapping(1:total) <= 0) .or. any(ids(1:total) <= 0)) stop 15
  print '(A)', 'PASS Fortran conversion and ordering'
end program

subroutine arret(code)
  implicit none
  integer, intent(in) :: code
  if (code /= 2) stop 16
  stop 2
end subroutine
