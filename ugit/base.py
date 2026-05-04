import os

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

def is_ignored(path):
  return '.ugit' in path.split('/')

  #TODO actually create the tree object