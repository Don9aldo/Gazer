# Build file for windows executable.
# Requires pyinstaller script to be in PATH or PYINSTALLER_PATH env variable
# to be set to pyinstaller script location.
from __future__ import print_function, division, unicode_literals
import os
import platform

from subprocess import check_output

app_name = 'gazer'
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print("Project root:", project_root)
pyinstaller_path = os.getenv('PYINSTALLER_PATH', 'pyinstaller')
lib_path = os.path.join(project_root, 'lib')
hook_path = os.path.join(project_root, 'hooks')
target = os.path.join(project_root, 'scripts', 'gazer_run.py')
out_path = os.path.join(project_root, 'dist')
build_path = os.path.join(project_root, 'build')
architecture = platform.architecture()[0]
icon = '../gazer/assets/logo/Gazer-Logo-Square-256px.ico'


def get_ops(debug=False):
    default_opts = ['--clean ',
                    '-y ',
                    '-p "{project_root}" '.format(project_root),
                    '--paths="{lib_path}" '.format(lib_path),
                    '--additional-hooks-dir="{hook_path}" '.format(hook_path),
                    '--distpath="{out_path}" '.format(out_path),
                    '--workpath="{build_path}" '.format(build_path),
                    '--icon "{icon}"'.format(icon),
                    '--onefile ',
                    '--noconsole '
                    ]

    if not debug:
        app_file_name = '{}.{}'.format(app_name, architecture)
        opts = default_opts + ['--name {app_file_name} '.format(app_file_name)]
    else:
        app_file_name = '{}-debug.{}'.format(app_name, architecture)
        opts = default_opts[:-2] + [
            '--name {app_file_name} '.format(app_file_name)]

    return ' '.join(opts)


command = '{pyinstaller} {opts} "{target}"'.format(pyinstaller=pyinstaller_path,
                                                   opts=get_ops(),
                                                   target=target)
print(command)
print(check_output(command, shell=True))

command = '{pyinstaller} {opts} "{target}"'.format(pyinstaller=pyinstaller_path,
                                                   opts=get_ops(debug=True),
                                                   target=target)
print(command)
print(check_output(command, shell=True))

print('End of program.')
