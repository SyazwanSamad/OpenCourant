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
#include "dynamain.h"
#include <stdio.h>
DynakeyMessages dynakeymessages;


// DynakeyMessages
void DynakeyMessages::ShowMessage(const sdiMessageHandler::Level &level, int code, va_list args) const
{
    int type = 0;
    switch(level)
    {
    case sdiMessageHandler::Warning: type = 1; break;
    case sdiMessageHandler::Error:   type = 2; break;
    default:                         type = 0;
    }

    const hwReaderMessage& message = const_cast<DynakeyMessages*>(this)->Add(code, type, args,
        "", "", "", 0);
}
 
 
#include <sdiCFGTypeMapper.h> 
#include <sdiModelViewPO.h>
#include <sdiModelViewPOLSDyna.h>

static std::vector<IMECPreObject *> pre_obj_lst[HCDI_OBJ_TYPE_HC_MAX];

#include <MODEL_IO/solverCDR.h>
#include <MODEL_IO/cfgio_model_factory_reader_po_exprtk.h>
 
extern "C" DYNAKEY_DECLS
sdi::ModelViewEdit* DynakeyReadModel(const char *filename)
{
    std::string msgfilename = getenv("HM_MSG_DIR");
#if defined WIN32 || _WIN32
    msgfilename += "\\CONFIG\\";
#else
    msgfilename += "/CONFIG/";
#endif
    msgfilename += "msg_hw_radioss_reader.txt";

    // Initialize message pool
    dynakeymessages.ReadMessageFile(msgfilename);
    dynakeymessages.SetOffset(100000);

    std::string str_error, filenameLoc;
    // This makes relying on the environment variables
    string rootDir;

    vector<string>  allowable_vec{ "HM_SUPPORTED" };
    string str_version("Keyword971_R14.1");
    const CFGKernel* kernel = MultiCFGKernelMgr::getInstance().InitCFGKernel(rootDir, "", str_version, filenameLoc, false, allowable_vec, str_error);
    if(!kernel)
    {
        if(str_error.empty()) str_error = "Could not initialize configuration profile " + str_version;
        dynakeymessages.Add(9001, 3, "", 0, str_error.c_str());
        fprintf(stderr, "OpenReader: %s\n", str_error.c_str());
        return nullptr;
    }
    FILE* input = fopen(filename, "rb");
    if(!input)
    {
        const std::string error = std::string("Cannot open LS-DYNA input file ") + filename;
        dynakeymessages.Add(9001, 3, filename, 0, error.c_str());
        fprintf(stderr, "OpenReader: %s\n", error.c_str());
        return nullptr;
    }
    fclose(input);

    SolverSyntaxInfos syntaxSolverInfos;
    SolverInputInfo solverInf;
    ModelFactoryReaderPOExprTk* model = new ModelFactoryReaderPOExprTk();
    CommonDataReaderCFG reader(model,"", str_version, "", true);
    for(auto& objects : pre_obj_lst)
    {
        for(IMECPreObject *object : objects) delete object;
        objects.clear();
    }
    reader.ReadModel(filename, pre_obj_lst);
    sdi::ModelViewPO* pModelViewSDI = new sdi::SDIModelViewPOLSDyna(pre_obj_lst);
    pModelViewSDI->ApplyIdOffsets("INCLUDE_TRANSFORM");

    return pModelViewSDI;
}

extern "C" DYNAKEY_DECLS
DynakeyMessages& DynakeyGetMessages()
{
    return dynakeymessages;
}

