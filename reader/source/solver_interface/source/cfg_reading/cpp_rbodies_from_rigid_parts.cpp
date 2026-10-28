//Copyright>        OpenCourant
//Copyright>        Copyright (C) 2026 OpenCourant contributors
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
//Copyright>        This file is part of OpenCourant, a fork of OpenRadioss.
//Copyright>        See COPYRIGHT.md at the root of the repository for the full
//Copyright>        copyright and attribution statement.
#include "GlobalModelSDI.h"
#include <dll_settings.h>
#include <sdiModelView.h>
#include <sdiEntity.h>
#include <sdiSelection.h>
#include <sdiElement.h>
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <limits>
#include <map>
#include <set>
#include <stdexcept>
#include <vector>

using namespace sdi;

namespace
{
struct RigidPart
{
    HandleRead handle;
    int id;
    int count;
    int mode;
    std::vector<sdiUIntList> regions;
};

std::vector<RigidPart> parts;
std::vector<int> bodyIds;
std::vector<int> partIds;
bool evaluated = false;
bool created = false;

void Require(bool ok, const char *message)
{
    if(!ok) throw std::runtime_error(message);
}

int FortranId(size_t id)
{
    Require(id <= static_cast<size_t>(std::numeric_limits<int>::max()),
            "entity ID exceeds the Starter integer range");
    return static_cast<int>(id);
}

std::vector<sdiUIntList> ConnectedRegions(const EntityRead& part)
{
    ModelViewEdit *model = Get_ModelViewSDI();
    std::vector<sdiUIntList> elements, regions;
    std::map<unsigned int, std::vector<size_t>> incident;
    SelectionElementRead selection(part);
    while(selection.Next())
    {
        sdiUIntList nodes;
        selection->GetNodeIds(nodes);
        nodes.erase(std::remove(nodes.begin(), nodes.end(), 0), nodes.end());
        for(unsigned int node : nodes)
        {
            HandleRead handle;
            Require(model->FindById("/NODE", node, handle), "rigid part references a missing element node");
            incident[node].push_back(elements.size());
        }
        elements.push_back(nodes);
    }
    std::set<unsigned int> visited;
    // Component IDs follow element order; node sets use the reference reader's depth-first order.
    for(const sdiUIntList& element : elements)
        for(unsigned int seed : element)
        {
            if(visited.count(seed)) continue;
            regions.emplace_back();
            sdiUIntList pending(1, seed);
            while(!pending.empty())
            {
                unsigned int node = pending.back();
                pending.pop_back();
                if(!visited.insert(node).second) continue;
                regions.back().push_back(node);
                for(size_t index : incident.at(node))
                    for(unsigned int next : elements[index])
                        if(!visited.count(next)) pending.push_back(next);
            }
        }
    Require(regions.size() <= static_cast<size_t>(std::numeric_limits<int>::max()),
            "rigid-part region count exceeds the Starter integer range");
    return regions;
}

std::vector<RigidPart> ReadParts()
{
    Require(Get_ModelViewSDI() != nullptr, "no loaded model");
    std::vector<RigidPart> result;
    SelectionRead selection(Get_ModelViewSDI(), "/PART");
    while(selection.Next())
    {
        int flag = 0;
        sdiValue value;
        if(selection->GetValue(sdiIdentifier("IRIGID"), value))
            Require(value.GetValue(flag), "invalid /PART IRIGID type");
        std::vector<sdiUIntList> regions;
        if(flag == 2) regions = ConnectedRegions(*selection);
        result.push_back({selection->GetHandle(), FortranId(selection->GetId()),
                          flag == 2 ? static_cast<int>(regions.size()) : flag == 1 ? 1 : 0,
                          flag, std::move(regions)});
    }
    return result;
}

void ValidateParts()
{
    const std::vector<RigidPart> current = ReadParts();
    Require(current.size() == parts.size(), "parts changed after rigid-part evaluation");
    for(size_t i = 0; i < parts.size(); ++i)
        Require(current[i].handle == parts[i].handle && current[i].id == parts[i].id &&
                current[i].mode == parts[i].mode && current[i].regions == parts[i].regions &&
                current[i].count == parts[i].count, "parts changed after rigid-part evaluation");
}

void Evaluate(int *counts)
{
    if(!created)
    {
        parts = ReadParts();
        evaluated = true;
    }
    else ValidateParts();
    Require(counts != nullptr || parts.empty(), "null rigid-part count array");
    size_t total = 0;
    for(size_t i = 0; i < parts.size(); ++i)
    {
        total += parts[i].count;
        Require(total <= static_cast<size_t>(std::numeric_limits<int>::max()),
                "rigid-body count exceeds the Starter integer range");
        counts[i] = parts[i].count;
    }
}

struct Field
{
    const char *source;
    const char *target;
    const char *reference;
};

const Field fields[] = {
    {"Node_ID", "independentnode", "/NODE"},
    {"Skew_ID", "SKEW_CSID", "/SKEW"},
    {"Sens_ID", "ISENSOR", "/SENSOR"},
    {"Mass", "MASS", nullptr},
    {"JXX", "JXX", nullptr}, {"JYY", "JYY", nullptr}, {"JZZ", "JZZ", nullptr},
    {"JXY", "JXY", nullptr}, {"JYZ", "JYZ", nullptr}, {"JXZ", "JXZ", nullptr}
};

struct PreparedPart
{
    HandleRead include;
    sdiString title;
    sdiValue unit;
    std::vector<sdiValue> values;
    int id;
    int mode;
    std::vector<sdiUIntList> regions;
};

PreparedPart Prepare(const RigidPart& part)
{
    ModelViewEdit *model = Get_ModelViewSDI();
    EntityRead entity(model, part.handle);
    PreparedPart result;
    result.include = entity.GetInclude();
    result.title = entity.GetName();
    result.id = part.id;
    result.mode = part.mode;
    result.regions = part.regions;
    Require(entity.GetValue(sdiIdentifier("unitid"), result.unit), "cannot read part units");
    if(part.mode == 1) for(const Field& field : fields)
    {
        sdiValue value;
        if(field.reference)
        {
            EntityType type = model->GetEntityType(field.reference);
            value = sdiValue(sdiValueEntity(type, 0));
            entity.GetValue(sdiIdentifier(field.source), value);
            sdiValueEntity reference;
            Require(value.GetValue(reference), "invalid rigid-part reference type");
            HandleRead handle;
            Require(reference.GetId() == 0 || model->FindById(type, reference.GetId(), handle),
                    "rigid part references a missing node, skew, or sensor");
        }
        else
        {
            value = sdiValue(0.0);
            entity.GetValue(sdiIdentifier(field.source), value);
        }
        result.values.push_back(value);
    }
    return result;
}

class IncludeScope
{
public:
    IncludeScope(ModelViewEdit *model, HandleRead include) : model(model), previous(model->SetCurrentCollector(include)) {}
    ~IncludeScope() { model->SetCurrentCollector(previous); }
private:
    ModelViewEdit *model;
    HandleRead previous;
};

void Create(int *mapping, int *ids)
{
    Require(evaluated, "rigid-part creation requires evaluation on the current model");
    ValidateParts();
    if(!created)
    {
        std::vector<PreparedPart> prepared;
        for(size_t i = 0; i < parts.size(); ++i)
        {
            if(parts[i].count) prepared.push_back(Prepare(parts[i]));
        }
        Require((mapping && ids) || prepared.empty(), "null rigid-part output array");
        ModelViewEdit *model = Get_ModelViewSDI();
        std::vector<HandleEdit> added;
        size_t total = 0;
        for(const PreparedPart& part : prepared) total += part.mode == 1 ? 1 : part.regions.size();
        added.reserve(2 * total);
        bodyIds.reserve(total);
        partIds.reserve(total);
        try
        {
            for(const PreparedPart& part : prepared)
            for(size_t region = 0; region < (part.mode == 1 ? 1 : part.regions.size()); ++region)
            {
                IncludeScope include(model, part.include);
                HandleEdit setHandle, bodyHandle;
                const bool connected = part.mode == 2;
                const sdiUIntList members = connected ? part.regions[region] : sdiUIntList(1, part.id);
                const sdiString number = std::to_string(region + 1);
                Require(model->CreateEntity(setHandle, "/SET/GENERAL", "Rigid Part:" + std::to_string(part.id) +
                        (connected ? " Component:" + number : "")),
                        "cannot create rigid-part set");
                added.push_back(setHandle);
                EntityEdit set(model, setHandle);
                Require(set.SetValue(sdiIdentifier("unitid"), part.unit) &&
                        set.SetValue(sdiIdentifier("clausesmax"), sdiValue(1)) &&
                        set.SetValue(sdiIdentifier("KEY_type", 0, 0), sdiValue(sdiString(connected ? "NODE" : "PART"))) &&
                        set.SetValue(sdiIdentifier("idsmax", 0, 0), sdiValue(FortranId(members.size()))) &&
                        set.SetValue(sdiIdentifier("ids", 0, 0),
                            sdiValue(sdiValueEntityList(model->GetEntityType(connected ? "/NODE" : "/PART"), members))),
                        "cannot populate rigid-part set");
                Require(model->CreateEntity(bodyHandle, "/RBODY", "/RBODY Automatically generated from /PART Id: " +
                        std::to_string(part.id) + (connected ? " component: " + number + "/" +
                        std::to_string(part.regions.size()) : " title: " + part.title)), "cannot create rigid-part body");
                added.push_back(bodyHandle);
                EntityEdit body(model, bodyHandle);
                Require(body.SetValue(sdiIdentifier("unitid"), part.unit) &&
                        body.SetValue(sdiIdentifier("dependentnodeset"),
                            sdiValue(sdiValueEntity(setHandle.GetType(), setHandle.GetId(model)))),
                        "cannot assign rigid-part body set or units");
                for(size_t i = 0; i < part.values.size(); ++i)
                    Require(body.SetValue(sdiIdentifier(fields[i].target), part.values[i]),
                            "cannot copy rigid-part body field");
                partIds.push_back(part.id);
                bodyIds.push_back(FortranId(body.GetId()));
            }
            created = true;
        }
        catch(...)
        {
            for(auto it = added.rbegin(); it != added.rend(); ++it) model->Delete(*it);
            bodyIds.clear();
            partIds.clear();
            throw;
        }
    }
    if(bodyIds.empty()) return;
    Require(mapping && ids, "null rigid-part output array");
    std::copy(partIds.begin(), partIds.end(), mapping);
    std::copy(bodyIds.begin(), bodyIds.end(), ids);
}

}

[[noreturn]] void GlobalModelSDIConversionFailure()
{
    // The legacy void ABI cannot return failure; do not let Starter use a partial model.
    try { throw; }
    catch(const std::exception& error) { std::fprintf(stderr, "OpenReader rigid-part conversion failed: %s\n", error.what()); }
    catch(...) { std::fprintf(stderr, "OpenReader rigid-part conversion failed: unknown exception\n"); }
    std::exit(EXIT_FAILURE);
}

void GlobalModelSDIResetRigidParts()
{
    parts.clear();
    partIds.clear();
    bodyIds.clear();
    evaluated = false;
    created = false;
}

extern "C"
{
CDECL void cpp_evaluate_rbodies_number_from_rigid_parts_(int *counts)
{
    try { Evaluate(counts); }
    catch(...) { GlobalModelSDIConversionFailure(); }
}
CDECL void cpp_evaluate_rbodies_number_from_rigid_parts(int *counts) { cpp_evaluate_rbodies_number_from_rigid_parts_(counts); }
CDECL void cpp_evaluate_rbodies_number_from_rigid_parts__(int *counts) { cpp_evaluate_rbodies_number_from_rigid_parts_(counts); }
CDECL void CPP_EVALUATE_RBODIES_NUMBER_FROM_RIGID_PARTS(int *counts) { cpp_evaluate_rbodies_number_from_rigid_parts_(counts); }

CDECL void cpp_create_rbodies_from_rigid_parts_(int *mapping, int *ids)
{
    try { Create(mapping, ids); }
    catch(...) { GlobalModelSDIConversionFailure(); }
}
CDECL void cpp_create_rbodies_from_rigid_parts(int *mapping, int *ids) { cpp_create_rbodies_from_rigid_parts_(mapping, ids); }
CDECL void cpp_create_rbodies_from_rigid_parts__(int *mapping, int *ids) { cpp_create_rbodies_from_rigid_parts_(mapping, ids); }
CDECL void CPP_CREATE_RBODIES_FROM_RIGID_PARTS(int *mapping, int *ids) { cpp_create_rbodies_from_rigid_parts_(mapping, ids); }
}
