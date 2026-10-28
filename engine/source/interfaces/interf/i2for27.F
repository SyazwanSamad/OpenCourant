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
!||    i2for27       ../engine/source/interfaces/interf/i2for27.F
!||--- called by ------------------------------------------------------
!||    intti2f       ../engine/source/interfaces/interf/intti2f.F
!||--- calls      -----------------------------------------------------
!||    i2for27_cin   ../engine/source/interfaces/interf/i2for27_cin.F
!||    i2for27_pen   ../engine/source/interfaces/interf/i2for27_pen.F
!||    i2mom27_cin   ../engine/source/interfaces/interf/i2mom27_cin.F
!||--- uses       -----------------------------------------------------
!||====================================================================
      SUBROUTINE I2FOR27(X, V, VR, A, AR, MS, IN, STIFN, STIFR, WEIGHT, IRECTM, NSV, IRTLM, DR, DL, FINI, STFN_PEN,
     . STFR_PEN, FSAV, FNCONT, IPENA, VISC, CSTS, MSR, ADI, SMAS, SINER, MMAS, SAV_FOR_PENA, MS_PENA, NOINT, NODNX_SMS,
     . DMINT2, DT2T, NELTST, ITYPTST, NSN, NMN, IDEL2, PENFLAG, IROT, SKEW, SAV_INER_POFF, DPARA, MSEGTYP2, CSTS_BIS,
     . T2FAC_SMS, FNCONTP, FTCONTP)
C-----------------------------------------------
C   M o d u l e s
C-----------------------------------------------
#include      "implicit_f.inc"
C-----------------------------------------------
C   D u m m y   A r g u m e n t s
C-----------------------------------------------
      INTEGER  NSN,NMN,NOINT,NELTST,ITYPTST,IDEL2,PENFLAG,IROT
      INTEGER  IRECTM(4,*),NSV(*),MSR(*),IRTLM(*),WEIGHT(*),
     .   NODNX_SMS(*),IPENA(*),MSEGTYP2(*)
      my_real
     .   VISC,DT2T
      my_real
     .   X(3,*),V(3,*),A(3,*),VR(3,*),AR(3,*),MS(*),IN(*),FINI(6,4,*),
     .   DL(3,4,*),DR(3,4,*),STIFN(*),STIFR(*),STFN_PEN(*),STFR_PEN(*),
     .   FSAV(*),FNCONT(3,*),DMINT2(4,*),SAV_FOR_PENA(8,*),MS_PENA(*),
     .   CSTS(2,*),SMAS(*),MMAS(*),SINER(*),ADI(*),SKEW(9,*),CSTS_BIS(2,*),
     .   T2FAC_SMS(*),FNCONTP(3,*)   ,FTCONTP(3,*) 
      my_real
     .   SAV_INER_POFF(*),DPARA(7,*)
#include      "com01_c.inc"
C-----------------------------------------------
C   L o c a l   V a r i a b l e s
C-----------------------------------------------
      INTEGER I,NINDXC,NINDXP
      INTEGER INDXC(NSN),INDXP(NSN)
C=======================================================================
      INDXC(1:NSN) = 0      
      INDXP(1:NSN) = 0 
      NINDXC = 0     
      NINDXP = 0     
C----------------          
      DO I=1,NSN
        IF (IPENA(I) == 0) THEN     
          NINDXC = NINDXC + 1     
          INDXC(I) = I              
        ELSE                        
          NINDXP = NINDXP + 1     
          INDXP(I) = I              
        ENDIF                       
      ENDDO
c-----------
      IF (NINDXC > 0) THEN
      CALL I2FOR27_CIN(NSN, NMN, A, IRECTM, CSTS, MSR, NSV, IRTLM, MS, WEIGHT, STIFN, MMAS, IDEL2, SMAS, X, V, FSAV,
     . FNCONT, INDXC, IN, SINER, DPARA, MSEGTYP2, AR, STIFR, CSTS_BIS, T2FAC_SMS, FNCONTP, FTCONTP)
c
        IF (IRODDL /= 0) THEN
      CALL I2MOM27_CIN(NSN, NMN, AR, IRECTM, CSTS, MSR, NSV, IRTLM, IN, MS, A, X, WEIGHT, STIFR, STIFN, IDEL2, SMAS,
     . SINER, MMAS, ADI, INDXC, SAV_INER_POFF, MSEGTYP2, CSTS_BIS)
        ENDIF
      ENDIF
c
      IF (NINDXP > 0) THEN
      CALL I2FOR27_PEN(X, V, VR, A, AR, MS_PENA, IN, STIFN, STIFR, WEIGHT, NSV, IRTLM, CSTS, SKEW, DL, DR, FINI, FSAV,
     . FNCONT, NSN, STFN_PEN, STFR_PEN, VISC, PENFLAG, IROT, NOINT, NODNX_SMS, DMINT2, SAV_FOR_PENA, IRECTM, DT2T,
     . NELTST, ITYPTST, INDXP, SAV_INER_POFF, MSEGTYP2, FNCONTP, FTCONTP)
c
      ENDIF                                                            
c-----------
      RETURN
      END SUBROUTINE I2FOR27
C
