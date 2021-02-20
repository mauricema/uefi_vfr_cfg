#!/usr/bin/env python
## @ BuildUtility.py
# Build bootloader main script
#
# Copyright (c) 2016 - 2020, Intel Corporation. All rights reserved.<BR>
# SPDX-License-Identifier: BSD-2-Clause-Patent
#
##

import os
import sys
import re
import marshal
#sys.path.insert (0, 'BootloaderCorePkg/Tools')
from GenCfgDataOrg import CGenCfgData

class DscToYaml ():
    def __init__ (self):
        self._HdrKeyList = ['EMBED', 'STRUCT']
        self._BsfKeyList = ['NAME','HELP','TYPE','PAGE', 'PAGES', 'OPTION','CONDITION','ORDER', 'MARKER', 'SUBT', 'FIELD']
        self.GenCfgData = None
        self.CfgRegExp  = re.compile("^([_a-zA-Z0-9$\(\)]+)\s*\|\s*(0x[0-9A-F]+|\*)\s*\|\s*(\d+|0x[0-9a-fA-F]+)\s*\|\s*(.+)")
        self.BsfRegExp  = re.compile("(%s):{(.+?)}(?:$|\s+)" % '|'.join(self._BsfKeyList))
        self.HdrRegExp  = re.compile("(%s):{(.+?)}" % '|'.join(self._HdrKeyList))
        self.Prefix     = ''


    def LoadConfigDataFromDsc (self, FileName):
        GenCfgData = CGenCfgData()
        if FileName.endswith('.pkl'):
            with open(FileName, "rb") as PklFile:
                GenCfgData.__dict__ = marshal.load(PklFile)
        elif FileName.endswith('.dsc'):
            if GenCfgData.ParseDscFile(FileName) != 0:
                raise Exception(GenCfgData.Error)
            if GenCfgData.CreateVarDict() != 0:
                raise Exception(GenCfgData.Error)
        else:
            raise Exception('Unsupported file "%s" !' % FileName)
        GenCfgData.UpdateDefaultValue()
        self.GenCfgData = GenCfgData

    def PrintDscLine (self):
        for line in self.GenCfgData._DscLines:
            print (line)

    def FormatTemplateName (self, text, parts):
        return text

    def FormatValue (self, field, text, indent = ''):
        if (not text.startswith('!expand')) and (': ' in text):
            tgt = ':' if field == 'option' else '- '
            text = text.replace(': ', tgt)
        lines = text.splitlines()
        if len(lines) == 1 and field != 'help':
            return text
        else:
            return '>\n   ' + '\n   '.join ([indent + i.lstrip() for i in lines])

    def ParseCfgLine (self, DscLine, ConfigDict, InitDict):
        InitDict.clear ()
        if DscLine.startswith('gCfgData.'):
            Match = self.CfgRegExp.match(DscLine[9:])
            if not Match:
                return False
            ConfigDict['cname']  = self.Prefix + Match.group(1)
            Value  = Match.group(4).strip()
            Length = Match.group(3).strip()
            ConfigDict['length'] = Length
            ConfigDict['value'] = Value
            return True

        Match = re.match("^\s*#\s+(!BSF|!HDR)\s+(.+)", DscLine)
        if not Match:
            return False

        Remaining = Match.group(2)
        if Match.group(1) == '!BSF':
            Result = self.BsfRegExp.findall (Remaining)
            if not Result:
                return False

            for Each in Result:
                Key = Each[0].lower()
                Val = Each[1]
                if Key == 'field':
                    Name = Each[1]
                    if ':' not in Name:
                        raise Exception ('Incorrect bit field format !')
                    Parts = Name.split(':')
                    ConfigDict['length'] = Parts[1]
                    ConfigDict['cname']  = '@' + Parts[0]
                    return True
                elif Key == 'pages' or Key == 'page':
                    InitDict = dict(ConfigDict)
                    ConfigDict.clear()
                    ConfigDict['cname'] = '$ACTION'
                    ConfigDict['page'] = Val
                    return True
                elif Key == 'subt':
                    ConfigDict.clear()
                    Parts = Each[1].split(':')
                    TmpName = Parts[0][:-5]
                    Skey = Parts[0].lower()
                    if TmpName == 'CFGHDR':
                        CfgTag = '_$FFF_'
                        Sval = '!expand { %s_TMPL : [ ' % TmpName + '%s, %s, ' % (Parts[1], CfgTag) + ', '.join (Parts[2:]) + ' ] }'
                    else:
                        Sval = '!expand { %s_TMPL : [ ' % TmpName + ', '.join (Parts[1:]) + ' ] }'
                    ConfigDict.clear()
                    ConfigDict['cname']  = TmpName
                    ConfigDict['expand'] = Sval
                    return True
                else:
                    if Key in ['name', 'help', 'option'] and Val.startswith('+'):
                        Val = ConfigDict[Key] + '\n' +  Val[1:]
                    if Val.strip() == '':
                        Val = "''"
                    ConfigDict[Key] = Val

        else:
            Match = self.HdrRegExp.match(Remaining)
            if not Match:
                return False
            Key = Match.group(1)
            Remaining = Match.group(2)
            if Key  == 'EMBED':
                Parts = Remaining.split(':')
                Names = Parts[0].split(',')
                if Parts[-1] == 'END':
                    Prefix = '>'
                else:
                    Prefix = '<'
                Skip = False
                if Parts[1].startswith('TAG_'):
                    TagTxt = '%s:%s' % (Names[0], Parts[1])
                else:
                    TagTxt = Names[0]
                    if Parts[2] in ['START', 'END']:
                        if Names[0] == 'PCIE_RP_PIN_CTRL[]':
                            Skip = True
                        else:
                            TagTxt = '%s:%s' % (Names[0], Parts[1])
                if not Skip:
                    ConfigDict.clear()
                    ConfigDict['cname'] = Prefix + TagTxt
                    return True

            if Key  == 'STRUCT':
                Text = Remaining.strip()
                ConfigDict[Key.lower()] = Text

        return False


    def ProcessDscLines (self, Lines):
        Cfgs = []
        ConfigDict = dict()
        InitDict   = dict()
        for Line in Lines:
            Ret = self.ParseCfgLine (Line, ConfigDict, InitDict)
            if Ret:
                if Cfgs and Cfgs[-1]['cname'][0] != '@' and ConfigDict['cname'][0] == '@':
                    # it is a bit field, mark the previous one as virtual
                    Cname = Cfgs[-1]['cname']
                    NewCfg = dict(Cfgs[-1])
                    NewCfg['cname'] = '@$STRUCT'
                    Cfgs[-1].clear ()
                    Cfgs[-1]['cname'] = Cname

                    Cfgs.append(NewCfg)

                if Cfgs and Cfgs[-1]['cname'] == 'CFGHDR' and ConfigDict['cname'][0] == '<':
                    # swap CfgHeader and the CFG_DATA order
                    if ':' in ConfigDict['cname']:
                        # replace the real TAG for CFG_DATA
                        Cfgs[-1]['expand'] = Cfgs[-1]['expand'].replace('_$FFF_', '0x%s' % ConfigDict['cname'].split(':')[1][4:])
                    Cfgs.insert (-1, ConfigDict)
                else:
                    Cfgs.append (ConfigDict)

                ConfigDict = dict(InitDict)
        return Cfgs


    def FormatName (self, Name):
        return Name


    def VariableFixup (self, Each):
        fix_dict = {
          '$Pcie'         :  '$PCIE_RP_CFG_DATA.Pcie',
          '$Hda'          :  '$HDA_CFG_DATA.Hda',
          '$Dsp'          :  '$HDA_CFG_DATA.Dsp',
          '$PlatformId'   :  '$PLATFORMID_CFG_DATA.PlatformId',
          '$$(1).Enable'  :  '$PID_GPIO_CFG_DATA.$(1).Enable',
          '$$(1)_Half0'   :  '$GPIO_CFG_DATA.$(1)_Half0',
        }
        Key = Each
        Val = self.GenCfgData._MacroDict[Each]
        for each in fix_dict:
            Val = Val.replace (each, fix_dict[each])
        return Key, Val


    def TemplateFixup (self, TmpName, TmpList):
        if TmpName in ['CFGHDR_TMPL']:
            Find = '((_LENGTH_$(1)_+8)/4):10b, $(2):4b, $(3):4b, _TAG_$(1)_:12b'
            for Each in TmpList:
                if Each['cname'] == 'CfgHeader':
                    Each['value'] = Each['value'].replace(Find, '((_LENGTH_$(1)_)/4):10b, $(3):4b, $(4):4b, $(2):12b')

        return


    def ConfigFixup (self, CfgList):
        SwapIdx = []
        for Idx, Cfg in enumerate(CfgList):
            # For QEMU
            if Cfg['cname'] in ['GpioItemSize', 'GpioItemCount']:
                Cfg['value'] = Cfg['value'].replace('(_OFFSET_GPIO_DATA_GPP_A1_ - _OFFSET_GPIO_DATA_GPP_A0_)', '8')
                if Cfg['cname'] in ['GpioItemCount']:
                    Cfg['value'] = Cfg['value'].replace('_LENGTH_GPIO_CFG_HDR_', '_LENGTH_GPIO_CFG_HDR_ - 8')

            elif Cfg['cname'] == 'SiliconTest3':
                Cfg['value'] = '{0:0W, ' + Cfg['value'][1:]

            elif Cfg['cname'] == 'SiliconTest4':
                Cfg['value'] = '{0:0D, ' + Cfg['value'][1:]

            if re.match('<GPIO_CFG_HDR(:*)?', Cfg['cname']):
                SwapIdx.append (Idx)

        for Idx in SwapIdx:
            CfgList[Idx], CfgList[Idx + 1] = CfgList[Idx + 1], CfgList[Idx]

        return


    def OutputVariable (self):
        Lines = []
        for Each in self.GenCfgData._MacroDict:
            Key, Value = self.VariableFixup (Each)
            Lines.append ('%-30s : %s' % (Key,  Value))
        return Lines


    def OutputTemplate (self):
        Lines = []
        TemplateDict = dict()
        for TmpName in self.GenCfgData._BsfTempDict:

            Text = self.GenCfgData._BsfTempDict[TmpName]
            TmpList = self.ProcessDscLines (Text)
            self.TemplateFixup (TmpName, TmpList)
            TemplateDict[TmpName] = TmpList

            Lines.append ('%s: >' % TmpName)
            Lines.extend (self.OutputDict (TmpList))
            Lines.append ('\n')

        return Lines


    def OutputConfig (self):
        Lines = []
        for Idx, Line in enumerate (self.GenCfgData._DscLines):
            if Line.startswith('[PcdsDynamicVpd.Upd]'):
                break

        Cfgs = self.ProcessDscLines (self.GenCfgData._DscLines[Idx+1:])
        self.ConfigFixup (Cfgs)

        Lines.extend (self.OutputDict (Cfgs))

        return Lines

    def OutputDict (self, Cfgs):
        Lines = []
        Level = 0
        for Each in Cfgs:
            Name   = Each['cname']
            Prefix = Name[0]

            if Prefix == '<':
                Level += 1
                if Level == 1:
                    Lines.append ('')

            Padding = '  ' * Level
            if Prefix not in '<>@':
                Padding += '  '
            else:
                Name = Name[1:]
                if Prefix == '@':
                    Padding += '    '

            if ':' in Name:
                Parts = Name.split(':')
                Name = Parts[0]
                #if len(Parts) > 1 and not Parts[1].startswith('TAG_'):
                #    if Name.endswith('[]'):
                #        Name = Parts[1]

            if Prefix != '>':
                if 'expand' in Each:
                    Lines.append ('%s- %s' % (Padding, Each['expand']))
                else:
                    Lines.append ('%s- %-12s :' % (Padding , self.FormatName (Name)))
            else:
                if Level == 1:
                    Lines.append ('')


            for Field in Each:
                if Field in ['cname', 'expand']:
                    continue
                ValueStr = self.FormatValue (Field, Each[Field], Padding + ' ' * 16)
                Lines.append ('  %s  %-12s : %s' % (Padding, Field, ValueStr))

            if Prefix == '>':
                Level -= 1
                if Level == 0:
                    Lines.append ('')

        return Lines

def Usage ():
    print ('\n'.join([
          "Dsc2Yaml Version 0.5",
          "Usage:",
          "    python  Dsc2Yaml.py  DscFile  YamlBaseName"
          ]))

def main():

    dsc2yaml = DscToYaml ()

    argn = len(sys.argv)
    if argn < 2 or argn > 3:
        Usage ()
        return 0

    dsc_file = sys.argv[1]
    if argn == 2:
        base_name = 'CfgDataDef.yaml'
    else:
        base_name = sys.argv[2]

    parts = os.path.splitext(base_name)
    if parts[1] == '':
        parts[1] = '.yaml'

    dsc2yaml.LoadConfigDataFromDsc (dsc_file)

    if True:
        lines = dsc2yaml.OutputTemplate ()
        fo = open('CfgDataTemplate.yaml', 'w')
        for line in lines:
            fo.write(line + '\n')
        fo.close()

    if True:
        lines = dsc2yaml.OutputConfig ()
        fo = open('CfgDataOption.yaml', 'w')
        for line in lines:
            #print (line)
            fo.write(line[2:] + '\n')
        fo.close()

    if True:
        lines = dsc2yaml.OutputVariable ()
        fo = open('CfgDataVariable.yaml', 'w')
        for line in lines:
            #print (line)
            fo.write(line + '\n')
        fo.close()


if __name__ == '__main__':
    main ()

