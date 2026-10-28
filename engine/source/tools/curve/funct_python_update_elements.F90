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
!Copyright>        This file is part of OpenCourant, a fork of OpenRadioss.
!Copyright>        See COPYRIGHT.md at the root of the repository for the full
!Copyright>        copyright and attribution statement.
!||====================================================================
!||    funct_python_update_elements_mod   ../engine/source/tools/curve/funct_python_update_elements.F90
!||--- called by ------------------------------------------------------
!||    resol                              ../engine/source/engine/resol.F
!||    resol_alloc_python                 ../engine/source/engine/resol_alloc.F90
!||====================================================================
      module funct_python_update_elements_mod
        implicit none
      contains
!! \brief initialize the python elemental variables found in the python function
!||====================================================================
!||    funct_python_update_elements   ../engine/source/tools/curve/funct_python_update_elements.F90
!||--- called by ------------------------------------------------------
!||    resol                          ../engine/source/engine/resol.F
!||    resol_alloc_python             ../engine/source/engine/resol_alloc.F90
!||--- calls      -----------------------------------------------------
!||    result_quad_scalar              ../engine/source/tools/element_results/result_quad_scalar.F90
!||    result_shell_scalar             ../engine/source/tools/element_results/result_shell_scalar.F
!||    result_solid_scalar             ../engine/source/tools/element_results/result_solid_scalar.F
!||    python_element_sync            ../engine/source/mpi/python_spmd_mod.F90
!||    schlieren_buffer_gathering     ../engine/source/output/anim/generate/schlieren_buffer_gathering.F
!||--- uses       -----------------------------------------------------
!||    ale_connectivity_mod           ../common_source/modules/ale/ale_connectivity_mod.F
!||    aleanim_mod                    ../common_source/modules/aleanim_mod.F
!||    elbufdef_mod                   ../common_source/modules/mat_elem/elbufdef_mod.F90
!||    result_quad_scalar_mod          ../engine/source/tools/element_results/result_quad_scalar.F90
!||    matparam_def_mod               ../common_source/modules/mat_elem/matparam_def_mod.F90
!||    multi_fvm_mod                  ../common_source/modules/ale/multi_fvm_mod.F90
!||    mvsiz_mod                      ../engine/share/spe_inc/mvsiz_mod.F90
!||    my_alloc_mod                   ../common_source/tools/memory/my_alloc.F90
!||    my_dealloc_mod                 ../common_source/tools/memory/my_dealloc.F90
!||    names_and_titles_mod           ../common_source/modules/names_and_titles_mod.F
!||    nodal_arrays_mod               ../common_source/modules/nodal_arrays.F90
!||    precision_mod                  ../common_source/modules/precision_mod.F90
!||    python_funct_mod               ../common_source/modules/python_mod.F90
!||    python_spmd_mod                ../engine/source/mpi/python_spmd_mod.F90
!||    stack_mod                      ../engine/share/modules/stack_mod.F
!||====================================================================
        subroutine funct_python_update_elements(py, ispmd, &
        &   n2d,  ngroup,  nixc, nixtg, nixs, nixq, &
        &   numgeo, numelc, numeltg, numels,numelq, nummat, numnod, &
        &   nparg, npropg, npropm, npropmi, npropgi, &
        &   snercvois, snesdvois, slercvois, slesdvois, &
        &   sthke, seani,&
        &   elbuf_tab   ,iparg       ,geo        , &
        &   ixc         ,ixtg,     ixs, ixq, pm          ,bufmat     , &
        &   ehour       , &
        &   ipm         ,igeo      ,thke      ,err_thk_sh4 ,err_thk_sh3, &
        &   nodes        ,w           ,ale_connect, &
        &   nercvois  ,nesdvois  ,lercvois    ,lesdvois, &
        &   n0phas, nvphas,stack       ,          &
        &   multi_fvm , &
        &   mat_param, fani_cell    ,itherm)

! ----------------------------------------------------------------------------------------------------------------------
!                                                     Module
! ----------------------------------------------------------------------------------------------------------------------
          use precision_mod, only : WP
          use python_funct_mod, only : python_
          use python_spmd_mod, only : python_element_sync
          use elbufdef_mod, only : ELBUF_STRUCT_
          use stack_mod, only : STACK_PLY
          use multi_fvm_mod, only : MULTI_FVM_STRUCT
          use ale_connectivity_mod, only : T_ALE_CONNECTIVITY
          use names_and_titles_mod, only: ncharline100
          use matparam_def_mod, only: MATPARAM_STRUCT_
          use aleanim_mod  , only : fani_cell_
          use result_quad_scalar_mod, only : result_quad_scalar
          use nodal_arrays_mod, only : nodal_arrays_
          use mvsiz_mod, only : MVSIZ
! ----------------------------------------------------------------------------------------------------------------------
!                                                     implicit none
! ----------------------------------------------------------------------------------------------------------------------
          use my_alloc_mod
          use my_dealloc_mod, only : my_dealloc
          implicit none
! ----------------------------------------------------------------------------------------------------------------------
!                                                     Arguments
! ----------------------------------------------------------------------------------------------------------------------
          type(python_),intent(inout) :: py !< the Fortran structure that holds the python functions
          integer, intent(in) :: ispmd !< current MPI rank
          integer, intent(in) :: n2d !< is 2d model
          integer, intent(in) :: ngroup !< number of element groups
          integer, intent(in) :: nixc !< shell connectivity size
          integer, intent(in) :: nixtg !< triangle connectivity size
          integer, intent(in) :: nixs !< solid connectivity size
          integer, intent(in) :: nixq !< quad connectivity size
          integer, intent(in) :: numgeo !< size of geo array
          integer, intent(in) :: numelc !< number of shell elements
          integer, intent(in) :: numeltg !< number of triangle elements
          integer, intent(in) :: numels !< number of solid elements
          integer, intent(in) :: numelq !< number of quad elements
          integer, intent(in) :: nummat !< number of materials
          integer, intent(in) :: numnod !< number of nodes
          integer, intent(in) :: nparg !< size of iparg array
          integer, intent(in) :: npropg !< size of geo array
          integer, intent(in) :: npropm !< size of pm array
          integer, intent(in) :: npropmi !< size of ipm array
          integer, intent(in) :: npropgi !< size of igeo array
          integer, intent(in) :: snercvois !< size of nercvois array
          integer, intent(in) :: snesdvois !< size of nesdvois array
          integer, intent(in) :: slercvois !< size of lercvois array
          integer, intent(in) :: slesdvois !< size of lesdvois array
          integer, intent(in) :: sthke !< size of thke array
          integer, intent(in) :: seani !< size of ehour array
          integer, intent(in) :: n0phas !< law 51 phases
          integer, intent(in) :: nvphas !< law 51 phases
          integer, intent(in) :: itherm
          TYPE(nodal_arrays_), intent(inout) :: nodes
          real(kind=WP), intent(inout) :: w(3,numnod) !< for ALE?
          real(kind=WP), intent(inout) :: thke(sthke) !< thickness of shell elements ?
          real(kind=WP), intent(inout) :: ehour(seani) !< working array ?
          real(kind=WP), intent(inout) :: geo(npropg,numgeo) !< property array
          real(kind=WP), intent(inout) :: pm(npropm,nummat) !< property array
          real(kind=WP), intent(inout) :: err_thk_sh4(numelc) !< ?
          real(kind=WP), intent(inout) :: err_thk_sh3(numeltg) !< ?
          integer, intent(inout) :: iparg(nparg,ngroup) !< element group properties
          integer, intent(inout) :: ixc(nixc,numelc) !< shell connectivity array
          integer, intent(inout) :: ixtg(nixtg,numeltg) !< triangle connectivity array
          integer, intent(inout) :: ixs(nixs,numels) !< solid connectivity array
          integer, intent(inout) :: ixq(nixq,numelq) !< quad connectivity array
          integer, intent(inout) :: ipm(npropmi,nummat) !< property array
          integer, intent(inout) :: igeo(npropgi,numgeo) !< property array
          integer, intent(inout) :: nercvois(snercvois) !< for Schlieren option
          integer, intent(inout) :: nesdvois(snesdvois) !< for Schlieren option
          integer, intent(inout) :: lercvois(slercvois) !< for Schlieren option
          integer, intent(inout) :: lesdvois(slesdvois) !< for Schlieren option
          type(ELBUF_STRUCT_), dimension(ngroup), intent(inout), target :: elbuf_tab !< element buffer structure
          type(STACK_PLY), intent(inout) :: stack !< tack structure
          type(MULTI_FVM_STRUCT), intent(in) :: multi_fvm !< finite volume structure
          real(kind=WP), intent(in) :: bufmat(*) !< buffer material ?
          type(T_ALE_CONNECTIVITY), intent(in) :: ale_connect !< ALE connectivity structure
          type(MATPARAM_STRUCT_), dimension(nummat), intent(in) :: mat_param !< material parameters
          type(FANI_CELL_), intent(in) :: fani_cell !< ALE cell animation structure
! ----------------------------------------------------------------------------------------------------------------------
!                                                   Local variables
! ----------------------------------------------------------------------------------------------------------------------
          integer :: ii,j,ng,i
          real(kind=WP), dimension(:), allocatable :: scalar_results
          integer :: mds_matid(0)
          integer, allocatable :: valid_results(:)
          logical :: zero_default
          integer :: idmds
          integer :: imdsvar
          integer :: ipt_input
          integer :: ply_input
          integer :: layer_input
          integer :: iuvar_input
          integer :: id
          integer :: mode
          integer :: ity
          character(len=ncharline100) :: keyword
! ----------------------------------------------------------------------------------------------------------------------
!                                                      Body
! ----------------------------------------------------------------------------------------------------------------------
          if(py%elements%global%n > 0) then
            !-----------------------------------------------------------!
            ! Default material, layer, and integration-point selectors
            !-----------------------------------------------------------!
            idmds = 0
            imdsvar = 0
            ipt_input = -2
            layer_input = -2
            ply_input = -2
            iuvar_input = -2
            id = -1
            mode = -1
            call my_alloc(scalar_results, MVSIZ, "scalar_results")
            call my_alloc(valid_results, MVSIZ, "valid_results")
            !-------------------------------------------------------!
            !     LOOP OVER ELEM GROUPS & OUTPUT DATA               !
            !-------------------------------------------------------!
            scalar_results(1:MVSIZ) = -HUGE(scalar_results(1))
            do ii = 1, py%elements%local%n
              ng = py%elements%local%group_id(ii)
              j = py%elements%local%local_id(ii)
              ity = iparg(5,ng)
              do i = 1,ncharline100
                keyword(i:i) = py%elements%local%keyword(ii)%result(i:i)
                if(ichar(keyword(i:i)) == 0) keyword(i:i) = " "
              end do
              if(ity == 3 .or. ity == 7 ) then
                ! shell or triangle
                !-------------------------------------------------------!
                !     SCHLIEREN INITIALIZATION (IF DEFINED)             !
                !       DENSITY FOR ALL TRIA ARE STORED IN WA_L         !
                !-------------------------------------------------------!
                ! /TRIA uses the shared three-node element buffer.
                if(keyword == "SCHLIEREN" .and. n2d > 0)then
                  call schlieren_buffer_gathering(nercvois ,nesdvois ,lercvois ,lesdvois, iparg, elbuf_tab, multi_fvm,itherm)
                end if

                CALL RESULT_SHELL_SCALAR( &
                & elbuf_tab, scalar_results, iparg, geo, ixc, &
                & ixtg, pm, bufmat, ehour, ipm, &
                & igeo, thke, err_thk_sh4, err_thk_sh3, nodes%x, &
                & nodes%v, w, ale_connect, stack, layer_input, &
                & ipt_input, ply_input, iuvar_input, keyword, nodes%d, &
                & ng, multi_fvm, idmds, imdsvar, mds_matid, &
                & id, mode, mat_param, valid_results, zero_default)
              else if (ity == 1) then ! solid
                CALL RESULT_SOLID_SCALAR( &
                & elbuf_tab, scalar_results, iparg, ixs, pm, &
                & bufmat, ehour, ipm, nodes%x, nodes%v, &
                & w, ale_connect, layer_input, -1, -1, &
                & -1, iuvar_input, 0, keyword, fani_cell, &
                & multi_fvm, ng, idmds, imdsvar, id, &
                & mat_param, mode, valid_results)

              else if (ity == 2) then ! quad
                CALL RESULT_QUAD_SCALAR( &
                & ng, n0phas, nvphas, ngroup, n2d, &
                & numelq, nummat, numnod, nparg, npropm, &
                & npropmi, ispmd, elbuf_tab, scalar_results, iparg, &
                & ixq, NIXQ, pm, ehour, ipm, &
                & nodes%x, nodes%v, w, ale_connect, layer_input, &
                & iuvar_input, keyword, bufmat, multi_fvm, id, &
                & mat_param, valid_results)

              end if
              py%elements%local%values(ii) = scalar_results(j)
              !write(6,*) "keyword",keyword(1:10),"value",scalar_results(j)

            end do

            call my_dealloc(scalar_results)
            call my_dealloc(valid_results)

            call python_element_sync(py%elements)



          end if
          return
        end subroutine funct_python_update_elements
      end module funct_python_update_elements_mod



