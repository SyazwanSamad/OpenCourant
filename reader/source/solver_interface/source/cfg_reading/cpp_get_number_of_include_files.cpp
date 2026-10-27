//Copyright>        OpenRadioss
//Copyright>        Copyright (C) 2026 Siemens
//Copyright>
//Copyright>        This program is free software: you can redistribute it and/or modify
//Copyright>        it under the terms of the GNU Affero General Public License as published by
//Copyright>        the Free Software Foundation, either version 3 of the License, or
//Copyright>        (at your option) any later version.
//Copyright>
//Copyright>        This program is distributed in the hope that it will be useful,
//Copyright>        but WITHOUT ANY WARRANTY; without even the implied warranty of
//Copyright>        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//Copyright>        GNU Affero General Public License for more details.
//Copyright>
//Copyright>        You should have received a copy of the GNU Affero General Public License
//Copyright>        along with this program.  If not, see <https://www.gnu.org/licenses/>.
//Copyright>
//Copyright>
//Copyright>        OpenCourant
//Copyright>        Copyright (C) 2026 OpenCourant contributors
//Copyright>
//Copyright>        Modified by the OpenCourant project, 2026.
//Copyright>        Modifications are licensed under the GNU Affero General Public
//Copyright>        License, version 3 or (at your option) any later version.
//Copyright>
//Copyright>        This file is part of OpenCourant, a fork of OpenRadioss.
//Copyright>        See COPYRIGHT.md at the root of the repository for the full
//Copyright>        copyright and attribution statement.

#include "GlobalModelSDI.h"

#include <dll_settings.h>

extern "C" 
{

void CDECL cpp_get_number_of_include_files_(int *isDyna, int *nbIncludes)
{
    try { GlobalModelSDICountIncludeFiles(*isDyna, nbIncludes); }
    catch(...) { GlobalModelSDIQueryFailure(); }
}

void CDECL CPP_GET_NUMBER_OF_INCLUDE_FILES(int *isDyna, int *nbIncludes)
{cpp_get_number_of_include_files_ (isDyna, nbIncludes);}

void CDECL cpp_get_number_of_include_files__(int *isDyna, int *nbIncludes)
{cpp_get_number_of_include_files_ (isDyna, nbIncludes);}

void CDECL cpp_get_number_of_include_files(int *isDyna, int *nbIncludes)
{cpp_get_number_of_include_files_ (isDyna, nbIncludes);}


}
