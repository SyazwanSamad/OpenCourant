Copyright>        OpenRadioss
Copyright>        Copyright (C) 2026 Siemens
Copyright>
Copyright>        This program is free software: you can redistribute it and/or modify
Copyright>        it under the terms of the GNU Affero General Public License as published by
Copyright>        the Free Software Foundation, either version 3 of the License, or
Copyright>        (at your option) any later version.
Copyright>
Copyright>        This program is distributed in the hope that it will be useful,
Copyright>        but WITHOUT ANY WARRANTY; without even the implied warranty of
Copyright>        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
Copyright>        GNU Affero General Public License for more details.
Copyright>
Copyright>        You should have received a copy of the GNU Affero General Public License
Copyright>        along with this program.  If not, see <https://www.gnu.org/licenses/>.
Copyright>
Copyright>
Copyright>        This file is part of OpenCourant, a fork of OpenRadioss.
Copyright>        See COPYRIGHT.md at the root of the repository for the full
Copyright>        copyright and attribution statement.
!||====================================================================
!||    schlieren_mod                ../engine/share/modules/schlieren_mod.F
!||--- called by ------------------------------------------------------
!||    dfunc0                       ../engine/source/output/anim/generate/dfunc0.F
!||    dfuncc                       ../engine/source/output/anim/generate/dfuncc.F
!||    dfuncs                       ../engine/source/output/anim/generate/dfunc6.F
!||    result_quad_scalar            ../engine/source/tools/element_results/result_quad_scalar.F90
!||    result_shell_scalar           ../engine/source/tools/element_results/result_shell_scalar.F
!||    result_solid_scalar           ../engine/source/tools/element_results/result_solid_scalar.F
!||    schlieren_buffer_gathering   ../engine/source/output/anim/generate/schlieren_buffer_gathering.F
!||====================================================================
      MODULE SCHLIEREN_MOD
#include "my_real.inc"

      my_real, DIMENSION(:), ALLOCATABLE :: WA_L

      END MODULE SCHLIEREN_MOD
