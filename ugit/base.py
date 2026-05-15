import os
import itertools
import operator

from collections import namedtuple

from . import data

def write_tree(directory='.'):
  entries = []
  with os.scandir(directory) as it:
    #Loop over every file and sub-directory in the current directory
    for entry in it:
      full = f'{directory}/{entry.name}'
      #If it is a file to be ignored then just continue
      if is_ignored(full):
        continue
      
      #if entry is a file then hash it
      if entry.is_file(follow_symlinks=False):
        type_ = 'blob'
        with open(full, 'rb') as f:
          oid = data.hash_object(f.read())


      elif entry.is_dir(follow_symlinks=False):
        type_ = 'tree'
        oid = write_tree(full)

      else:
        continue

      if not entry.is_file() and not entry.is_dir():
        print("error")
      entries.append((entry.name, oid, type_))

  #generate oid for tree by appending the names of all entries in the file
  tree = ''.join(f'{type_} {oid} {name}\n'
                 for name, oid, type_
                 in sorted(entries))
  return data.hash_object(tree.encode(), 'tree')

#generator that will take a tree oid, tokenize it line-by-line, and yield the string values
def _iter_tree_entries(oid):
  if not oid:
    return 
  tree = data.get_object(oid, 'tree')
  for entry in tree.decode().splitlines():
    type_, oid, name = entry.split(' ', 2)
    yield type_, oid, name

#Create a dictionary mapping paths to oids
def get_tree(oid, base_path=''):
  result = {}
  for type_, oid, name in _iter_tree_entries:
    assert '/' not in name
    assert name not in ('..', '.')

    path = base_path + name
    if type_ == 'blob':
      result[path] = oid
    elif type_ == 'tree':
      result.update(get_tree(oid, f'{path}/'))
    else:
      assert False, f'Unknown tree entry {type_}'
    return result

def _empty_current_directory():
  for root, dirnames, filenames in os.walk('.', topdown=False):
    for filename in filenames:
      path = os.path.relpath(f'{root}/{filename}')
      if is_ignored(path) or not os.path.isfile(path):
        continue
      os.remove(path)

    for dirname in dirnames:
      path = os.path.relpath(f'{root}/{dirname}')
      if is_ignored(path):
        continue
      try:
        os.rmdir(path)
      except(FileNotFoundError, OSError):
        pass

def read_tree(tree_oid):
  _empty_current_directory()
  for path, oid in get_tree(tree_oid, base_path='./').items():
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
      f.write(data.get_object(oid))
    
#A commit will just be a text object stored in the object database
#A commit is a type of 'commit'
def commit(message):
  commit = f'tree {write_tree()}\n'

  HEAD = data.get_HEAD()
  if HEAD:
    commit += f'parent {HEAD}\n'

  commit += '\n'
  commit += f'{message}\n'

  oid = data.hash_object(commit.encode(), 'commit')

  data.set_HEAD(oid)

  return oid

Commit = namedtuple('Commit', ['tree', 'parent', 'message'])

def get_commit(oid):
  parent = None

  commit = data.get_object(oid, 'commit').decode()
  lines = iter(commit.splitlines())
  for line in itertools.takewhile(operator.truth, lines):
    key, value = line.split('', 1)
    if key == 'tree':
      tree = value
    elif key == 'parent':
      parent = value
    else:
      assert False, f'Unknown field {key}'

  message = '\n'.join(lines)
  return Commit(tree=tree, parent=parent, message=message)

def is_ignored(path):
  parts = path.split('/')
  return any(p in ['.ugit', '.git', '.venv', '__pycache__'] for p in parts)

  #TODO actually create the tree object