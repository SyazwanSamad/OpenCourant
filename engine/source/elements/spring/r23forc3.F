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
!||    r23forc3           ../engine/source/elements/spring/r23forc3.F
!||--- called by ------------------------------------------------------
!||    forint             ../engine/source/elements/forint.F
!||--- calls      -----------------------------------------------------
!||    r23law108          ../engine/source/elements/spring/r23law108.F
!||    r23law113          ../engine/source/elements/spring/r23law113.F
!||    r23law114          ../engine/source/elements/spring/r23law114.F
!||    r23law135          ../engine/source/elements/spring/r23law135.F90
!||--- uses       -----------------------------------------------------
!||    elbufdef_mod       ../common_source/modules/mat_elem/elbufdef_mod.F90
!||    element_mod        ../common_source/modules/elements/element_mod.F90
!||    mat_elem_mod       ../common_source/modules/mat_elem/mat_elem_mod.F90
!||    python_funct_mod   ../common_source/modules/python_mod.F90
!||    r23law135_mod      ../engine/source/elements/spring/r23law135.F90
!||    sensor_mod         ../common_source/modules/sensor_mod.F90
!||    table_mod          ../engine/share/modules/table_mod.F
!||====================================================================
      SUBROUTINE R23FORC3(PYTHON, ELBUF_STR, JFT, JLT, NEL, MTN, IGEO, GEO, IPM, IXR, X, TABLE, XDP, F, NPF, TF, SKEW,
     . FLG_KJ2, VR, AR, V, DT2T, NELTST, ITYPTST, STIFN, STIFR, MS, IN, FSKY, IADR, SENSORS, OFFSET, ANIM, PARTSAV,
     . IPARTR, TANI, FR_WAVE, BUFMAT, BUFGEO, PM, RBY, FX1, FX2, FY1, FY2, FZ1, FZ2, MX1, MX2, MY1, MY2, MZ1, MZ2,
     . GRESAV, GRTH, IGRTH, MSRT, DMELRT, FLAG_SLIPRING_UPDATE, FLAG_RETRACTOR_UPDATE, JSMS, IGRE, NFT, PRELD1, STF_F,
     . STF, SANIN, IRESP, SNPC, mat_elem, NGRTH, NELEM, FLG_SPR_DT)

C-----------------------------------------------
C   M o d u l e s
C-----------------------------------------------
      USE python_funct_mod
      USE ELBUFDEF_MOD
      USE TABLE_MOD
      USE SENSOR_MOD
      use element_mod , only : nixr
      use mat_elem_mod
      use r23law135_mod
C-----------------------------------------------
C   I m p l i c i t   T y p e s
C-----------------------------------------------
#include      "implicit_f.inc"
C-----------------------------------------------
C   G l o b a l   P a r a m e t e r s
C-----------------------------------------------
#include      "mvsiz_p.inc"
C-----------------------------------------------
C   C o m m o n   B l o c k s
C-----------------------------------------------
#include      "param_c.inc"
#include      "com04_c.inc"
#include      "parit_c.inc"
#include      "com01_c.inc"
#include      "impl1_c.inc"
#include      "scr14_c.inc"
#include      "com08_c.inc"
#include      "scr02_c.inc"
#include      "scr18_c.inc"
#include      "task_c.inc"
C-----------------------------------------------
C   D u m m y   A r g u m e n t s
C-----------------------------------------------
      type(python_), intent(inout) :: PYTHON
      INTEGER, INTENT(IN) :: STF  !< Size of TF
      INTEGER, INTENT(IN) :: SANIN !< Size of ANIM
      INTEGER, INTENT(IN) :: IRESP  !< Single precision flag
      INTEGER, INTENT(IN) :: SNPC   !< Size of NPF
      INTEGER, INTENT(IN) :: IGRE
      INTEGER, INTENT(IN) :: NFT
      INTEGER, INTENT(IN) :: JSMS
      INTEGER, INTENT(IN) :: NGRTH
      INTEGER, INTENT(IN) :: NELEM
      INTEGER IXR(NIXR,*), NPF(*),IADR(3,*),IPARTR(*),
     .        IGEO(NPROPGI,*),JFT,JLT,NELTST ,ITYPTST,OFFSET,
     .        NEL,MTN,GRTH(*),IGRTH(*),FLG_KJ2,IPM(NPROPMI,*),FLAG_SLIPRING_UPDATE,
     .        FLAG_RETRACTOR_UPDATE
      INTEGER, INTENT(INOUT) :: FLG_SPR_DT
      my_real DT2T ,
     .   GEO(NPROPG,*),X(*),F(*),TF(STF),SKEW(LSKEW,*),FSKY(*),
     .   VR(*), V(*), AR(*), STIFN(*),STIFR(*),MS(*), IN(*),
     .   ANIM(SANIN),PARTSAV(*),TANI(15,*),
     .   FR_WAVE(*),BUFMAT(*),BUFGEO(*),PM(*),RBY(*),
     .   FX1(MVSIZ),FY1(MVSIZ),FZ1(MVSIZ),
     .   FX2(MVSIZ),FY2(MVSIZ),FZ2(MVSIZ),
     .   MX1(MVSIZ),MY1(MVSIZ),MZ1(MVSIZ),
     .   MX2(MVSIZ),MY2(MVSIZ),MZ2(MVSIZ),GRESAV(*),
     .   MSRT(*), DMELRT(*)
      my_real, INTENT(IN)          :: PRELD1,STF_F
      DOUBLE PRECISION XDP(3,*)
      TYPE(TTABLE) TABLE(*)
C
      TYPE (ELBUF_STRUCT_), TARGET :: ELBUF_STR
      TYPE (SENSORS_) , INTENT(IN) :: SENSORS
      type (mat_elem_) ,intent(inout) ,target :: mat_elem
      
C-----------------------------------------------
C   L o c a l   V a r i a b l e s
C-----------------------------------------------
      INTEGER :: NSENSOR


C=======================================================================
       NSENSOR = SENSORS%NSENSOR 
!
       IF(MTN  == 108) THEN
         ! Like type08 spring
      CALL R23LAW108(PYTHON, ELBUF_STR, JFT, JLT, NEL, MTN, IGEO, GEO, IPM, IXR, X, TABLE, XDP, F, NPF, TF, SKEW,
     . FLG_KJ2, VR, AR, V, DT2T, NELTST, ITYPTST, STIFN, STIFR, MS, IN, FSKY, IADR, NSENSOR, SENSORS%SENSOR_TAB, OFFSET,
     . ANIM, PARTSAV, IPARTR, TANI, BUFMAT, BUFGEO, PM, RBY, FX1, FX2, FY1, FY2, FZ1, FZ2, MX1, MX2, MY1, MY2, MZ1, MZ2,
     . GRESAV, GRTH, IGRTH, MSRT, DMELRT, JSMS, IGRE, NFT, STF, SANIN, IRESP, SNPC, FLG_SPR_DT)
       
       ELSEIF(MTN == 113) THEN
         ! Like type13 spring
      CALL R23LAW113(PYTHON, ELBUF_STR, JFT, JLT, NEL, MTN, IGEO, GEO, IPM, IXR, X, TABLE, XDP, F, NPF, TF, SKEW,
     . FLG_KJ2, VR, AR, V, DT2T, NELTST, ITYPTST, STIFN, STIFR, MS, IN, FSKY, IADR, NSENSOR, SENSORS%SENSOR_TAB, OFFSET,
     . ANIM, PARTSAV, IPARTR, TANI, FR_WAVE, BUFMAT, BUFGEO, PM, RBY, FX1, FX2, FY1, FY2, FZ1, FZ2, MX1, MX2, MY1, MY2,
     . MZ1, MZ2, GRESAV, GRTH, IGRTH, MSRT, DMELRT, JSMS, IGRE, NFT, PRELD1, STF_F, STF, SANIN, IRESP, SNPC, FLG_SPR_DT)
     .

       ELSEIF(MTN == 114) THEN
         ! seatbelt_element
      CALL R23LAW114(PYTHON, ELBUF_STR, JFT, JLT, NEL, MTN, IGEO, GEO, IPM, IXR, X, TABLE, XDP, F, NPF, TF, SKEW,
     . FLG_KJ2, VR, AR, V, DT2T, NELTST, ITYPTST, STIFN, STIFR, MS, IN, FSKY, IADR, SENSORS%SENSOR_TAB, OFFSET, ANIM,
     . PARTSAV, IPARTR, TANI, FR_WAVE, BUFMAT, BUFGEO, PM, RBY, FX1, FX2, FY1, FY2, FZ1, FZ2, MX1, MX2, MY1, MY2, MZ1,
     . MZ2, GRESAV, GRTH, IGRTH, MSRT, DMELRT, FLAG_SLIPRING_UPDATE, FLAG_RETRACTOR_UPDATE, JSMS, IGRE, NFT, NSENSOR,
     . STF, SANIN, IRESP, SNPC, FLG_SPR_DT)
       ELSEIF(MTN == 135) THEN
         FLG_KJ2 =1
      CALL R23LAW135(ELBUF_STR, NEL, IGEO, GEO, IPM, IXR, X, XDP, F, SKEW, VR, AR, V, STIFN, STIFR, FSKY, IADR,
     . NSENSOR, SENSORS%SENSOR_TAB, PARTSAV, IPARTR, TANI, FX1, FX2, FY1, FY2, FZ1, FZ2, MX1, MX2, MY1, MY2, MZ1, MZ2,
     . GRESAV, GRTH, IGRTH, IGRE, NFT, MAT_ELEM, NPROPG, LSKEW, IPARIT, INISPRI, SCODVER, ISMDISP, NUMELR, TT, DT1,
     . ANIM_FE, MTN, NGRTH, NELEM, NUMGEO, NUMMAT, NUMNOD, NPSAV, NGPE, NTHREAD, NUMSKW, LSKY)
     
 
       ENDIF
C-----------------------------------------------       
      RETURN
      END SUBROUTINE R23FORC3
