import sys
import re

str_db = []
var_db = {}

def load_hpk (hpk_file):
    fd = open (hpk_file, 'rb')
    hpk_bin = bytearray (fd.read())
    fd.close()
    id  = 2
    str_list = []
    str_list.extend ([''] * id)
    off = 0x45
    while True:
      if hpk_bin[off] == 0x21:
        # skip
        skip = hpk_bin[off+1] + 256 * hpk_bin[off+2]
        str_list.extend ([''] * skip)
        id += skip
        off+=3
        continue
      if hpk_bin[off] != 0x14:
        break
      txt  = []
      off += 1
      while hpk_bin[off] != 0:
        ch = hpk_bin[off]
        if ch >= 0x80:
          ch = ord('?')
        txt.append(chr(ch))
        off += 2
      if len(txt) >= 0:
        out = ''.join(txt)
        parts = out.split('\n')
        out = '\n'.join(list(filter(lambda x: len(x) > 0, parts)))
        str_list.append (out)
        id += 1
      off += 2
    return str_list

def print_form (root, level = 0):
    if root is None:
        return

    print ("%s *%s" % ('  ' * level, root['title']))
    #for cfg in root['cfgs']:
    #    print ("%s -%s %s %s" % ('  ' * level, cfg['prompt'], cfg['name'], '| '.join([x[1] for x in cfg['options']])))

    for form in root['child']:
        level += 1
        print_form(form, level)
        level -= 1

def build_form (form_txt):
    form   = {'title' : '', 'child' : [], 'id' : 0, 'link' : [], 'cfgs' : []}
    form['id'] = int(form_txt[0])
    cfg      = {}
    opt_type = None
    for line in form_txt[1:]:
      match = re.match ('title\s*=\s*STRING_TOKEN\s*\((.+)\);', line)
      if match:
        str_id = int(match.group(1), 0)
        form['title'] = '%s' % (str_db[str_id])
      match = re.match ('goto\s*(\d+),', line)
      if match:
        form['link'].append (int(match.group(1), 0))

      match = re.match ('(oneof|numeric|checkbox)\s*varid\s*=\s*(.+),', line)
      if match:
        opt_type = match.group(1)
        cfg = {'name' : match.group(2), 'prompt': '',  'help': '', 'options' : []}
        if opt_type == 'checkbox':
          cfg['options'] = [(0, 'Disable', '*'), (1, 'Enable', '')]
      if cfg:
        if 'CHECKBOX_DEFAULT' in line:
          cfg['options'] = [(0, 'Disable',  ''), (1, 'Enable', '*')]
        match = re.match ('prompt\s*=\s*STRING_TOKEN\s*\(*(.+)\),', line)
        if match:
          cfg['prompt'] = str_db[int(match.group(1), 0)]
        match = re.match ('help\s*=\s*STRING_TOKEN\s*\((.+)\),', line)
        if match:
          cfg['help'] = str_db[int(match.group(1), 0)]
        match = re.match ('(minimum|maximum|step|default)\s*=\s*(.+),', line)
        if match and opt_type == 'numeric':
          if len(cfg['options']) == 0:
            cfg['options'] = [0,0,0,0]
          if match.group(1) == 'minimum':
            idx = 0
          elif match.group(1) == 'maximum':
            idx = 1
          elif match.group(1) == 'default':
            idx = 2
          else:
            idx = 3
          val = match.group(2)
          if val.lower() == 'true':
            val = '1'
          if val.lower() == 'false':
            val = '0'
          cfg['options'][idx] = int(val, 0)

        match = re.match ('option\s*text\s*=\s*STRING_TOKEN\s*\((.+)\),\s*value\s*=\s*(.+),', line)
        if match:
          value = int(match.group(2), 0)
          if 'DEFAULT' in line:
            default = '*'
          else:
            default = ''
          option = (value, str_db[int(match.group(1), 0)], default)
          cfg['options'].append(option)

      match = re.match ('(endoneof|endnumeric|endcheckbox);', line)
      if match:
        form['cfgs'].append(dict(cfg))
        opt_type = None
        cfg = {}

    return form


def is_form_in_link (root, form_id):
    if form_id in root['link']:
      return True
    for each in root['child']:
      if is_form_in_link (each, form_id):
        return True
    return False


def build_root_link (root):
    for each in root['child']:
      if not is_form_in_link (root, each['id']):
        root['link'].append (each['id'])

def find_form_by_id (root, form_id):
    if root['id'] == form_id:
      return root
    for each in root['child']:
      ret = find_form_by_id (each, form_id)
      if ret is not None:
        return ret
    return None

def build_tree (root, node):
    tree = dict (node)
    tree['child'] = []
    for form_id in tree['link']:
      form = find_form_by_id (root, form_id)
      new  = build_tree (root, form)
      tree['child'].append(new)
    return tree

def parse_form (inc_file):
    global str_db
    fd = open (inc_file, 'r')
    lines = fd.readlines()
    fd.close()

    root      = {'title' : 'Root', 'child' : [],  'id' : 0, 'link' : [], 'cfgs' : []}
    level     = 0
    handle    = False
    form_txt  = None

    for line in lines:
      if line[0] == '#':
        continue
      line = line.strip()
      if line.startswith ('formset'):
        handle = True
        continue
      if line.startswith ('endformset;'):
        handle = False
        continue
      if not handle:
        continue

      if line.startswith ('form formid'):
        match = re.match ('form formid\s*=\s*(\d+)', line)
        form_id = int(match.group(1))
        level  += 1
        form_txt = ['%d' % form_id]
        continue

      if line.startswith ('endform;'):
        form = build_form (form_txt)
        root['child'].append (form)
        level -= 1
        form_txt = None
        continue

      if form_txt is not None:
        form_txt.append (line)

    build_root_link (root)

    return root



def build_pages (root, level = 0):
    if root is None:
        return

    parent = 'FM%02d' % (root['id'])
    for form in root['child']:
        child = 'FM%02d' % (form['id'])
        print ('  # !BSF PAGES:{%s:%s:"%s"}' % (child, parent, form['title']) )

        level += 1
        build_pages(form, level)
        level -= 1


def build_cfgs (root, level = 0):
    global var_db

    if root is None:
        return

    for form in root['child']:
        child = 'FM%02d' % (form['id'])
        for cfg in form['cfgs']:
          print ('  # !BSF PAGE:{%s}' % child)
          print ('  # !BSF NAME:{%s}' % cfg['prompt'])
          helps = cfg['help'].replace('\n', ' ')
          helps = helps.replace('\r', '')
          print ('  # !BSF HELP:{%s}' % (helps.strip()))
          default = 0
          if type(cfg['options'][0]) is type(1):
            cfgs = cfg['options']
            print ('  # !BSF TYPE:{EditNum, DEC, (%d,%d)}' % (cfgs[0], cfgs[1]))
            default = cfgs[2]
          else:
            print ('  # !BSF TYPE:{Combo}')
            options = ', '.join (['0x%x:%s' % (x[0], x[1]) for x in cfg['options']])
            print ('  # !BSF OPTION:{%s}' % options)
            for val, text, defval in cfg['options']:
              if defval == '*':
                default = val

          name = cfg['name'].split('.')[-1]
          name = name.replace ('[', '_')
          name = name.replace (']', '')

          if name not in var_db:
              parts = name.split('_')
              if len(parts) == 2:
                  dlen, dnum = var_db[parts[0]]
              else:
                  raise Exception ("Unknown size for '%s' !" % name)
          else:
              dlen, dnum = var_db[name]
              dlen = dlen * dnum

          print ('  gCfgData.%s  | * | 0x%02X | 0x%x' % (name, dlen, default))


        level += 1
        build_cfgs(form,  level)
        level -= 1

def build_root_pages (root, level = 0):
    for child in root['child'][0]['child']:
        print ('  # !BSF PAGES:{FM%02d::"%s"}' % (child['id'], child['title']) )
        build_pages (child)

    print ('\n\n\n')

    for idx, child in enumerate(root['child'][0]['child']):
        build_cfgs  (child)

def parse_vars (inc_file):
    fd = open (inc_file, 'r')
    lines = fd.readlines()
    fd.close()

    vars = dict()
    for line in lines:
        line = line.strip()
        if not line.endswith (';'):
            continue
        match = re.match ('(CHAR|UINT)(8|16|32|64)\s+(\w+)(\s*\[\s*(\d+)\s*\])?', line)
        if not match:
            continue

        if  match.group(5) is None:
            array_num = 1
        else:
            array_num = int (match.group(5))

        item_size = int (match.group(2)) // 8
        vars[match.group(3)] = (item_size, array_num)

    return vars


def usage():
    print ('\n'.join([
          "BiosVfr2Dsc Version 0.1",
          "Usage:",
          "    BiosVfr2Dsc  HpkDbFile  ComfinedVfrFile"
          ]))

def main ():
    global str_db
    global var_db

    if len(sys.argv) < 3:
        usage ()
        return 0

    hpk_file = sys.argv[1]
    vfr_file = sys.argv[2]
    str_db = load_hpk (hpk_file)
    var_db = parse_vars (vfr_file)

    debug  = 0
    # debug
    if debug:
        for idx, i in enumerate (str_db):
            print ('%04X: %s' % (idx, i))

    form   = parse_form (vfr_file)
    root   = build_tree (form, form)
    build_root_pages (root)

    return 0

if __name__ == '__main__':
    sys.exit(main())
