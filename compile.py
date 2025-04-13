import os
import six


if six.PY3:
    for root, dirs, files in os.walk('./'):
        if '__pycache__' in root:
            for file in files:
                if '.pyc' in file:
                    try:
                        new_filename=file[:file[:-4].rfind('.')]+'.pyc'
                        new_root=root.replace('/__pycache__', '')
                        os.rename(os.path.join(root, file), os.path.join(new_root, new_filename))
                    except:
                        pass
            os.rmdir(root)

for root, dirs, files in os.walk('./'):
    for file in files:
        if '.pyc' in file and 'controller' not in file and 'compile' not in file:
            try:
                os.remove(os.path.join(root, file[:-1]))
            except:
                pass

for root, dirs, files in os.walk('./log/'):
    for file in files:
        os.remove(os.path.join(root, file))

for root, dirs, files in os.walk('./param/'):
    for file in files:
        os.remove(os.path.join(root, file))

for root, dirs, files in os.walk('./.git/', topdown=False):
    for file in files:
        os.remove(os.path.join(root, file))
    for name in dirs:
        os.rmdir(os.path.join(root, name))
os.rmdir('./.git/')
