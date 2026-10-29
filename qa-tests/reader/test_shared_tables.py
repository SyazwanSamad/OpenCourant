# Copyright>        OpenCourant
# Copyright>        Copyright (C) 2026 OpenCourant contributors
# Copyright>
# Copyright>        This program is free software: you can redistribute it and/or modify
# Copyright>        it under the terms of the GNU Affero General Public License as published by
# Copyright>        the Free Software Foundation, either version 3 of the License, or
# Copyright>        (at your option) any later version.
# Copyright>
# Copyright>        This program is distributed in the hope that it will be useful,
# Copyright>        but WITHOUT ANY WARRANTY; without even the implied warranty of
# Copyright>        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# Copyright>        GNU Affero General Public License for more details.
# Copyright>
# Copyright>        You should have received a copy of the GNU Affero General Public License
# Copyright>        along with this program.  If not, see <https://www.gnu.org/licenses/>.
# Copyright>
# Copyright>
# Copyright>        This file is part of OpenCourant, a fork of OpenRadioss.
# Copyright>        See COPYRIGHT.md at the root of the repository for the full
# Copyright>        copyright and attribution statement.
"""Check inline table ownership and preservation of earlier Starter errors."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from rigid_parts.test_reader_contract import Reader, ROOT, INT, REF
from test_model_queries import dyna_load


def deck(explicit=False):
    text='*KEYWORD\n*NODE\n'
    for i, xyz in enumerate([(0,0,0),(1,0,0),(1,1,0),(0,1,0),(0,0,1),(1,0,1),(1,1,1),(0,1,1)],1):
        text+=f'{i:8d}'+''.join(f'{v:16g}' for v in xyz)+'\n'
    text+='*ELEMENT_SOLID\n'+''.join(''.join(f'{v:8d}' for v in [i,i,1,2,3,4,5,6,7,8])+'\n' for i in [1,2])
    text+='*SECTION_SOLID\n         1         1\n'
    for i in [1,2]:
        text+=f'*PART\ncube {i}\n{i:10d}{1:10d}{i:10d}\n'
        text+='*MAT_SIMPLIFIED_RUBBER_TITLE\nrubber\n'+f'{i:10d}{1e-9:10g}{100:10g}'+f'{0:10g}'*5+'\n'
        text+=f'{1:10g}'*3+f'{100:10d}{1:10g}{1:10g}{0:10g}{0:10g}\n'+f'{0:10d}'+f'{0:10g}'*4+'\n'
    table=('*DEFINE_TABLE_2D\n       100\n'+f'{0.1:20g}{101:20d}\n{1:20g}{102:20d}\n' if explicit
           else '*DEFINE_TABLE\n       100\n                 0.1\n                   1\n')
    curves=''
    for i in [101,102]:
        curves+='$ comment before header\n$ another comment\n*DEFINE_CURVE_TITLE\ncurve\n'+f'{i:10d}\n'
        curves+=''.join(f'{x:20g}{y:20g}\n' for x,y in [(0,0),(0.5,0.2),(1,1)])
    return text,table+curves


def probe(reader_path, folder):
    reader=Reader(reader_path)
    error,version=INT(),INT(2612)
    reader.library.hm_reader_variables(REF(error),REF(version))
    assert error.value==0
    assert dyna_load(reader,folder/'case.k',folder/'unused.rad')==0
    curves=reader.entities(b'/FUNCT',['id','numberofpoints'])
    materials=[]
    for _ in range(reader.count(b'MATERIAL')):
        reader.library.cpp_option_next()
        n=reader.integer('NL')
        materials.append({'id':reader.integer('id'),'NL':n,
            'functions':[reader.integer('FCT_ID_LI',i) for i in range(1,n+1)]})
    reader.load(ROOT/'qa-tests/reader/parameters/literal/rigid_0000.rad')
    assert reader.entities(b'/FUNCT',['id'])==[{'id':1}]
    assert dyna_load(reader,folder/'case.k',folder/'unused.rad')==0
    assert reader.entities(b'/FUNCT',['id','numberofpoints'])==curves
    (folder/'empty.k').write_text('*KEYWORD\n*END\n')
    assert dyna_load(reader,folder/'empty.k',folder/'unused.rad')==0
    assert reader.count(b'/FUNCT')==reader.count(b'MATERIAL')==0
    (folder/'reader.json').write_text(json.dumps({'curves':curves,'materials':materials}))


def listed_curves(listing):
    values={}
    for m in re.finditer(r'^\s*LOAD CURVE ID[^\n]*=\s*(\d+)',listing,re.M):
        points=[]
        for line in listing[m.end():].splitlines()[3:]:
            try: row=[float(v.replace('D','E')) for v in line.split()]
            except ValueError: break
            if len(row)!=2: break
            points.append(row)
        assert points,m.group(1)
        values[int(m.group(1))]=points
    return values


def run(args):
    args.output.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy()
    env.update(RAD_CFG_PATH=str(ROOT/'hm_cfg_files'),OMP_NUM_THREADS='1',KMP_STACKSIZE='400m')
    report=[]
    reference=None
    for name in ['inline','explicit','include','duplicate','identical_duplicate','missing']:
        if name=='missing' and not args.starter: continue
        folder=args.output/name
        folder.mkdir()
        base,table=deck(name not in ['inline','include'])
        if name=='include':
            (folder/'table.inc').write_text(table)
            text=base+'*INCLUDE\ntable.inc\n*END\n'
        else: text=base+table+'*END\n'
        if name in ['duplicate','identical_duplicate']:
            end=1 if name=='duplicate' else 0.2
            text=text.replace('*END',f'*DEFINE_CURVE\n       101\n{0:20g}{0:20g}\n{0.5:20g}{end:20g}\n{1:20g}{1:20g}\n*END')
        (folder/'case.k').write_text(text)
        command=[sys.executable,str(Path(__file__).resolve()),'--reader',str(args.reader),'--output',str(folder),'--probe']
        p=subprocess.run(command,capture_output=True,text=True,env=env,timeout=45)
        (folder/'reader.log').write_text(p.stdout+p.stderr)
        assert p.returncode==0,(name,p.stdout,p.stderr)
        model=json.loads((folder/'reader.json').read_text())
        assert all(row['numberofpoints']==3 for row in model['curves']),model
        ids=[row['id'] for row in model['curves']]
        assert len(ids)==(7 if 'duplicate' in name else 6),(name,ids)
        assert model['materials']==[{'id':1,'NL':3,'functions':[103,104,104]},
                                    {'id':2,'NL':3,'functions':[105,106,106]}],model
        if 'duplicate' not in name: assert len(set(ids))==6,ids
        if args.starter:
            if name=='missing':
                # Native LAW88 missing function: reach the table-copy failure boundary directly.
                fixture=ROOT/'qa-tests/reader/parameters/literal'
                for path in fixture.iterdir():
                    if path.is_file(): (folder/path.name).write_bytes(path.read_bytes())
                source=(fixture/'rigid_0000.rad').read_text()
                material='/MAT/LAW88/1\nrubber\n'+f'{1:20g}\n{0:20g}{100:20g}{0:20g}{0:10d}{1:10d}\n'
                material+=f'{0:10d}'+10*' '+f'{1:20g}{0:20g}{0:20g}{1:10d}\n{999:10d}'+10*' '+f'{1:20g}{0:20g}\n'
                (folder/'material.inc').write_text(material)
                (folder/'case_0000.rad').write_text(source)
            filename='case_0000.rad' if name=='missing' else 'case.k'
            p=subprocess.run([str(args.starter),'-i',filename,'-np','1'],cwd=folder,env=env,capture_output=True,text=True,timeout=60)
            (folder/'starter.log').write_text(p.stdout+p.stderr)
            listing=(folder/'case_0000.out').read_text(errors='replace')
            bad=name in ['duplicate','identical_duplicate','missing']
            assert p.returncode==(2 if bad else 0),(name,p.returncode,(p.stdout+p.stderr)[-2500:])
            assert 'forrtl: severe' not in (p.stdout+p.stderr).lower(),name
            assert bool(list(folder.glob('*.rst')))==(not bad),name
            if bad:
                assert re.search(r'ERROR ID\s*:\s*(79|779)',listing),listing[-2500:]
                assert 'NORMAL TERMINATION' not in listing and '0 ERROR(S)' not in listing
            else:
                values=listed_curves(listing)
                assert len(values)==6,values
                assert all(points==[[0,0],[0.5,0.2],[1,1]] for points in values.values()),values
                if reference is None: reference=values
                assert values==reference
            report.append({'case':name,'starter_exit':p.returncode,'functions':len(ids)})
        print('PASS shared tables: '+name,flush=True)
    if args.starter:
        for law in [123,125,132]:
            folder=args.output/f'law{law}'
            folder.mkdir()
            source=ROOT/'qa-tests/reader/rigid_parts/data/common.inc'
            mesh=re.sub(r'/MAT/LAW1/1.*?(?=/PROP)','',source.read_text(),flags=re.S)
            (folder/'common.inc').write_text(mesh)
            (folder/'case_0000.rad').write_bytes((Path(__file__).parent/f'shared_tables/law{law}.rad').read_bytes())
            p=subprocess.run([str(args.starter),'-i','case_0000.rad','-np','1'],cwd=folder,env=env,capture_output=True,text=True,timeout=60)
            (folder/'starter.log').write_text(p.stdout+p.stderr)
            listing=(folder/'case_0000.out').read_text(errors='replace')
            errors=re.findall(r'^ERROR ID\s*:\s*(\d+)',listing,re.M)
            # A later property error must not hide the duplicate emitted before material copying.
            assert errors==['79','3047'],(law,errors)
            assert re.search(r'\b2 ERROR\(S\)',listing),listing[-1000:]
            assert p.returncode==2 and not list(folder.glob('*.rst')),(law,p.returncode)
            assert 'forrtl: severe' not in (p.stdout+p.stderr).lower()
            report.append({'case':f'law{law}','starter_exit':p.returncode,'errors':errors})
            print(f'PASS shared tables: LAW{law} preserves earlier errors',flush=True)
    (args.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reader',required=True,type=lambda v:Path(v).resolve())
    p.add_argument('--starter',type=lambda v:Path(v).resolve())
    p.add_argument('--output',required=True,type=lambda v:Path(v).resolve())
    p.add_argument('--probe',action='store_true',help=argparse.SUPPRESS)
    args=p.parse_args()
    if args.probe: probe(args.reader,args.output)
    else: run(args)


if __name__=='__main__': main()
